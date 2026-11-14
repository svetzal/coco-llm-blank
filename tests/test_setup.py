import contextlib
import hashlib
import http.server
import importlib.util
import json
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('bootstrap', Path(__file__).parents[1] / 'scripts/setup.py')
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


def pdf_bytes():
    """Original two-page fixture: text followed by a blank page."""
    text = b'BT /F1 12 Tf 40 700 Td (Original starter kit test reference.) Tj ET'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
               b'<< /Length ' + str(len(text)).encode() + b' >>\nstream\n' + text + b'\nendstream',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>']
    output = b'%PDF-1.4\n'
    offsets = [0]
    for n, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output += f'{n} 0 obj\n'.encode() + obj + b'\nendobj\n'
    xref = len(output)
    output += f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode()
    output += b''.join(f'{offset:010} 00000 n \n'.encode() for offset in offsets[1:])
    output += f'trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    return output


class Handler(http.server.BaseHTTPRequestHandler):
    calls = 0

    def do_GET(self):
        type(self).calls += 1
        if self.path != '/reference.pdf':
            self.send_error(404)
            return
        body = pdf_bytes()
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.resource = {'id': 'test-book', 'title': 'Original fixture',
                         'url': 'https://colorcomputerarchive.com/repo/test.pdf',
                         'sha256': hashlib.sha256(pdf_bytes()).hexdigest()}
        (self.root / 'resources.json').write_text(json.dumps([self.resource]))

    @contextlib.contextmanager
    def server(self):
        Handler.calls = 0
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        worker = threading.Thread(target=server.serve_forever)
        worker.start()
        try:
            yield f'http://127.0.0.1:{server.server_port}'
        finally:
            server.shutdown()
            worker.join()
            server.server_close()

    def test_guidance_preserves_notes_and_rejects_implicit_target_change(self):
        for target in bootstrap.TARGETS:
            with self.subTest(target=target):
                root = self.root / target
                root.mkdir()
                shutil.copyfile(self.root / 'resources.json', root / 'resources.json')
                self.assertEqual(bootstrap.main(['--target', target, '--guidance-only'], root), 0)
                project = root / 'local/PROJECT.md'
                project.write_text(project.read_text() + '\nOwner notes.\n')
                saved = project.read_bytes()
                self.assertEqual(bootstrap.main(['--guidance-only'], root), 0)
                self.assertEqual(project.read_bytes(), saved)
                other = 'coco3' if target != 'coco3' else 'coco1'
                self.assertEqual(bootstrap.main(['--guidance-only', '--target', other], root), 1)
                self.assertEqual(project.read_bytes(), saved)

    def test_download_cache_and_tampering(self):
        destination = self.root / 'reference.pdf'
        with self.server() as url:
            resource = dict(self.resource, url=url + '/reference.pdf')
            bootstrap.fetch(resource, destination)
            self.assertEqual(destination.read_bytes(), pdf_bytes())
            bootstrap.fetch(resource, destination)
            self.assertEqual(Handler.calls, 1)
            destination.write_bytes(b'corrupted')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                bootstrap.fetch(resource, destination)
            self.assertEqual(Handler.calls, 1)

    def test_failed_downloads_leave_no_partial_file(self):
        with self.server() as url:
            for resource in [dict(self.resource, url=url + '/missing'),
                             dict(self.resource, url=url + '/reference.pdf', sha256='0' * 64)]:
                with self.assertRaises((OSError, ValueError)):
                    bootstrap.fetch(resource, self.root / 'reference.pdf')
                self.assertEqual(list(self.root.iterdir()), [self.root / 'resources.json'])

    @unittest.skipUnless(shutil.which('pdftotext'), 'Poppler required')
    def test_real_conversion_and_index(self):
        directory = self.root / 'local/references/test-book'
        directory.mkdir(parents=True)
        (directory / 'source.pdf').write_bytes(pdf_bytes())
        self.assertEqual(bootstrap.main(['--target', 'coco2'], self.root), 0)
        text = (directory / 'text.md').read_text()
        self.assertIn('Original starter kit test reference.', text)
        self.assertIn('## PDF page 2', text)
        metadata = json.loads((directory / 'extraction.json').read_text())
        self.assertEqual(metadata['pages'], 2)
        self.assertIn(2, metadata['sparse_pages'])
        self.assertIn('references/test-book/text.md', (self.root / 'local/INDEX.md').read_text())
        original = (directory / 'text.md').read_bytes()
        (directory / 'source.pdf').write_bytes(b'%PDF-broken')
        with self.assertRaises(subprocess.CalledProcessError):
            bootstrap.convert(self.resource, directory)
        self.assertEqual((directory / 'text.md').read_bytes(), original)

    @unittest.skipUnless(shutil.which('tesseract') and shutil.which('pdftoppm'), 'OCR tools required')
    def test_real_ocr_range_and_preservation_on_rerun(self):
        directory = self.root / 'local/references/test-book'
        directory.mkdir(parents=True)
        (directory / 'source.pdf').write_bytes(pdf_bytes())
        self.assertEqual(bootstrap.main(['--target', 'coco1', '--ocr', '--pages', '1:1'], self.root), 0)
        metadata = json.loads((directory / 'extraction.json').read_text())
        self.assertEqual(metadata['ocr_pages'], [1])
        self.assertIn('Original starter kit test reference', (directory / 'text.md').read_text())
        saved = (directory / 'text.md').read_bytes()
        self.assertEqual(bootstrap.main([], self.root), 0)
        self.assertEqual((directory / 'text.md').read_bytes(), saved)
        self.assertEqual(bootstrap.main(['--ocr', '--pages', '1:99'], self.root), 1)
        self.assertEqual((directory / 'text.md').read_bytes(), saved)

    def test_page_range_requires_ocr(self):
        self.assertEqual(bootstrap.main(['--pages', '1:2'], self.root), 1)
        self.assertFalse((self.root / 'local').exists())

    def test_failed_resource_returns_nonzero_and_remains_unconverted(self):
        directory = self.root / 'local/references/test-book'
        directory.mkdir(parents=True)
        (directory / 'source.pdf').write_bytes(b'corrupted')
        self.assertEqual(bootstrap.main(['--target', 'coco1'], self.root), 1)
        self.assertIn('not converted', (self.root / 'local/INDEX.md').read_text())

    def test_manifest_rejects_unsafe_paths_and_sources(self):
        for change in [{'id': '../outside'}, {'url': 'http://example.com/book.pdf'}, {'sha256': ''}]:
            (self.root / 'resources.json').write_text(json.dumps([dict(self.resource, **change)]))
            with self.assertRaises(ValueError):
                bootstrap.read_manifest(self.root / 'resources.json')

    def test_list_and_unknown_selection_do_not_initialize(self):
        self.assertEqual(bootstrap.main(['--list'], self.root), 0)
        self.assertEqual(bootstrap.main(['--resource', 'unknown'], self.root), 1)
        self.assertFalse((self.root / 'local').exists())


if __name__ == '__main__':
    unittest.main()

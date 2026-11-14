"""Original null-UI capture generator, guarded against source drift and reapplication."""

import hashlib

PRISTINE_SHA256 = "b813f70b890375c467dc1c7135e4172884ee659c1e6f63ef058f929d83cca85c"
CAPTURE = """static void capture_draw(void *sptr) {
    struct vo_interface *vo = sptr;
    struct vo_render *vr = vo->renderer;
    const char *path = getenv("DISPLAY_CAPTURE");
    if (!path) return;
    FILE *fp = fopen(path, "wb");
    if (!fp) { perror(path); exit(2); }
    fprintf(fp, "P6\\n%d %d\\n255\\n", vr->viewport.w, vr->viewport.h);
    for (int y=0; y<vr->viewport.h; ++y) {
        uint32_t *row = (uint32_t *)vr->buffer + y*vr->buffer_pitch;
        for (int x=0; x<vr->viewport.w; ++x) {
            uint8_t rgb[3] = { row[x] >> 24, row[x] >> 16, row[x] >> 8 };
            if (fwrite(rgb, 1, 3, fp) != 3) exit(2);
        }
    }
    if (fclose(fp)) exit(2);
}
static void capture_viewport(void *sptr, int w, int h) {
    struct vo_interface *vo = sptr;
    if (w>800 || h>600) exit(2);
    vo_render_set_viewport(vo->renderer, w, h);
    vo->renderer->buffer_pitch = w;
}
"""
INITIALIZE = """vo_interface_init(vo);
    struct vo_render *vr = vo_render_new(VO_RENDER_FMT_RGBA8);
    vo_set_renderer(vo, vr);
    vo_render_set_buffer(vr, calloc(800*600, sizeof(uint32_t)));
    vr->buffer_pitch = 640;
    vo->set_viewport = DELEGATE_AS2(void, int, int, capture_viewport, vo);
    vo->draw = DELEGATE_AS0(void, capture_draw, vo);"""


def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f"Expected exactly one replacement of {old!r}")
    return source.replace(old, new, 1)


def instrument(source: bytes) -> bytes:
    if hashlib.sha256(source).hexdigest() != PRISTINE_SHA256:
        raise ValueError("ui_null.c is not the pristine pinned source")
    text = replace_once(
        source.decode(), "#include <stdlib.h>", "#include <stdlib.h>\n#include <stdio.h>"
    )
    # Replace the declaration, retaining no upstream implementation in this package.
    start = text.index("static void null_render(")
    end = text.index("\nstatic void *new", start)
    text = replace_once(text, text[start:end], CAPTURE)
    text = replace_once(
        text,
        "struct vo_interface *vo = xmalloc(sizeof(*vo));",
        "struct vo_interface *vo = vo_interface_new(sizeof(*vo));",
    )
    text = replace_once(text, "*vo = (struct vo_interface){0};", INITIALIZE)
    text = replace_once(
        text,
        "\tvo->render_line = DELEGATE_AS3(void, unsigned, unsigned, uint8cp, null_render, vo->renderer);",
        "",
    )
    start = text.index("\nstatic void null_render(")
    text = replace_once(text, text[start:], "")
    return text.encode()

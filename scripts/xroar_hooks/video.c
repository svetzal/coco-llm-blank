/* coco.py test equipment, replacing the null UI's discarded video output in
 * XRoar's src/null/ui_null.c. Original code for the starter's instrumented
 * XRoar.
 *
 * The null UI normally throws every scanline away. This attaches XRoar's own
 * software renderer instead, so the machine's SAM/VDG (or GIME) output and
 * palette are rendered exactly as for a window, into a memory buffer. Nothing
 * here reads RAM or builds pixels.
 *
 * After the checkpoint, the first frame XRoar completes was partly scanned
 * before the checkpoint, so the second completed frame is written to the
 * COCO_VIDEO path as a binary PPM. It is the first frame rendered entirely
 * after the checkpoint.
 *
 * Log line on stderr: COCO_VIDEO,<tick>,<width>,<height>
 */
#define COCO_VIDEO_MAX_W 1024
#define COCO_VIDEO_MAX_H 768

static int coco_video_wait = -1;

void coco_video_checkpoint(void) {
	if (coco_video_wait < 0)
		coco_video_wait = 2;
}

static void coco_video_write(struct vo_render *vr, const char *path) {
	FILE *fp = fopen(path, "wb");
	if (!fp) {
		perror(path);
		exit(2);
	}
	fprintf(fp, "P6\n%d %d\n255\n", vr->viewport.w, vr->viewport.h);
	for (int y = 0; y < vr->viewport.h; ++y) {
		uint32_t *row = (uint32_t *)vr->buffer + y * vr->buffer_pitch;
		for (int x = 0; x < vr->viewport.w; ++x) {
			uint8_t rgb[3] = { row[x] >> 24, row[x] >> 16, row[x] >> 8 };
			if (fwrite(rgb, 1, 3, fp) != 3)
				exit(2);
		}
	}
	if (fclose(fp))
		exit(2);
	fprintf(stderr, "COCO_VIDEO,%u,%d,%d\n", (unsigned)event_current_tick,
	        vr->viewport.w, vr->viewport.h);
}

static void coco_video_draw(void *sptr) {
	struct vo_interface *vo = sptr;
	const char *path = getenv("COCO_VIDEO");
	if (!path || coco_video_wait <= 0 || --coco_video_wait > 0)
		return;
	coco_video_write(vo->renderer, path);
}

static void coco_video_viewport(void *sptr, int w, int h) {
	struct vo_interface *vo = sptr;
	if (w > COCO_VIDEO_MAX_W || h > COCO_VIDEO_MAX_H) {
		fprintf(stderr, "COCO_VIDEO_TOO_LARGE,%d,%d\n", w, h);
		exit(2);
	}
	vo_render_set_viewport(vo->renderer, w, h);
	vo->renderer->buffer_pitch = w;
}

static void coco_video_attach(struct vo_interface *vo) {
	vo_interface_init(vo);
	struct vo_render *vr = vo_render_new(VO_RENDER_FMT_RGBA8);
	vo_set_renderer(vo, vr);
	vo_render_set_buffer(vr, xmalloc(COCO_VIDEO_MAX_W * COCO_VIDEO_MAX_H * sizeof(uint32_t)));
	vr->buffer_pitch = COCO_VIDEO_MAX_W;
	vo->set_viewport = DELEGATE_AS2(void, int, int, coco_video_viewport, vo);
	vo->draw = DELEGATE_AS0(void, coco_video_draw, vo);
}

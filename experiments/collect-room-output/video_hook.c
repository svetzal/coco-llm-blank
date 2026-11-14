#include "events.h"
/* Original continuous capture of the real vo_render buffer, including boot.
 * S-video/zoomed is 512x192; record dimensions so changes cannot pass silently.
 */
static void capture_draw(void *sptr) {
    static FILE *fp;
    static unsigned frame;
    struct vo_interface *vo = sptr;
    struct vo_render *vr = vo->renderer;
    if (!fp) {
        const char *path = getenv("VIDEO_CAPTURE");
        if (!path || !(fp = fopen(path, "wb"))) exit(2);
    }
    for (int y = 0; y < vr->viewport.h; ++y) {
        uint32_t *row = (uint32_t *)vr->buffer + y * vr->buffer_pitch;
        for (int x = 0; x < vr->viewport.w; ++x) {
            uint8_t rgb[3] = { row[x] >> 24, row[x] >> 16, row[x] >> 8 };
            if (getenv("BROKEN_VIDEO")) rgb[0] = rgb[1] = rgb[2] = 0;
            if (fwrite(rgb, 1, 3, fp) != 3) exit(2);
        }
    }
    if (fflush(fp)) exit(2);
    fprintf(stderr, "VIDEO,%u,%u,%d,%d\n", frame++, (unsigned)event_current_tick,
            vr->viewport.w, vr->viewport.h);
}

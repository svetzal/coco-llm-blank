static void capture_draw(void *sptr) {
    struct vo_interface *vo = sptr;
    struct vo_render *vr = vo->renderer;
    static unsigned count;
    const char *path = getenv("CLEAN_CAPTURE");
    if (!path) return;
    if (++count > 1000) exit(2);
    FILE *fp = fopen(path, "ab");
    if (!fp) exit(2);
    fprintf(fp, "%u %u %d %d\n", count, (unsigned)event_current_tick,
            vr->viewport.w, vr->viewport.h);
    for (int y=0; y<vr->viewport.h; ++y) {
        uint32_t *row = (uint32_t *)vr->buffer + y*vr->buffer_pitch;
        unsigned char rgb[800*3];
        for (int x=0; x<vr->viewport.w; ++x) {
            rgb[3*x] = row[x] >> 24;
            rgb[3*x+1] = row[x] >> 16;
            rgb[3*x+2] = row[x] >> 8;
        }
        if (fwrite(rgb, 3, vr->viewport.w, fp) != (size_t)vr->viewport.w) exit(2);
    }
    if (fclose(fp)) exit(2);
}

/* Original test-only instrumentation. Inject keys through XRoar's API.
 * Never write RAM, CPU registers, PIA values or game state.
 */
static void collect_keyboard(const char *condition) {
    static unsigned frame;
    const char *frame_trap = getenv("COLLECT_FRAME_TRAP");
    const char *output = getenv("COLLECT_OUTPUT");
    if (frame_trap && output && !strcmp(condition, frame_trap)) {
        char path[4096];
        if (snprintf(path, sizeof(path), "%s/frame-%u.ram", output, frame)
                >= (int)sizeof(path)) exit(2);
        write_snapshot(path);
        fprintf(stderr, "FRAME,%u,%u\n", frame++, event_current_tick);
        if (frame == (unsigned)strtoul(getenv("COLLECT_FRAME_COUNT"), NULL, 10))
            xroar_set_timeout("0");
        return;
    }
    static FILE *events;
    static unsigned previous, number;
    const char *match = getenv("COLLECT_KEY_TRAP");
    const char *path = getenv("COLLECT_EVENTS");
    if (!match || !path || strcmp(condition, match)) return;
    if (!events) {
        events = fopen(path, "r");
        if (!events) { perror("collect events"); exit(2); }
    }
    char line[32];
    if (!fgets(line, sizeof(line), events)) {
        fprintf(stderr, "collect events exhausted\n"); exit(2);
    }
    const char names[] = "UDLRFM";
    const int keys[] = { DSCAN_UP, DSCAN_DOWN, DSCAN_LEFT,
        DSCAN_RIGHT, DSCAN_SPACE, DSCAN_M };
    unsigned next = 0;
    for (unsigned i = 0; i < 6; ++i)
        if (strchr(line, names[i])) next |= 1u << i;
    for (unsigned i = 0; i < 6; ++i) {
        unsigned bit = 1u << i;
        if ((previous & bit) && !(next & bit))
            keyboard_release(xroar.keyboard_interface, keys[i]);
        if (!(previous & bit) && (next & bit))
            keyboard_press(xroar.keyboard_interface, keys[i]);
    }
    previous = next;
    fprintf(stderr, "KEY,%u,%u,%u\n", number++, next, event_current_tick);
}

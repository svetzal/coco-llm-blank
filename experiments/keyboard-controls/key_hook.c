/* Original test instrumentation, included in XRoar xroar.c.
 * Only keyboard API calls: no CPU, RAM, PIA or scanner-result writes.
 * One line per sample: L=left, R=right, F=space, M=unrelated key, -=idle.
 */
static void experiment_keyboard(const char *condition) {
    static FILE *events;
    static unsigned previous;
    static unsigned sample_number;
    const char *match = getenv("KEYBOARD_TRAP");
    const char *path = getenv("KEYBOARD_EVENTS");
    if (!match || !path || strcmp(condition, match)) return;
    if (!events) {
        events = fopen(path, "r");
        if (!events) { perror("keyboard events"); exit(2); }
    }
    char line[32];
    if (!fgets(line, sizeof(line), events)) {
        fprintf(stderr, "keyboard events exhausted\n"); exit(2);
    }
    const char names[] = "LRFM";
    const int keys[] = { DSCAN_LEFT, DSCAN_RIGHT, DSCAN_SPACE, DSCAN_M };
    unsigned next = 0;
    for (unsigned i = 0; i < 4; ++i) {
        if (strchr(line, names[i])) next |= 1u << i;
    }
    for (unsigned i = 0; i < 4; ++i) {
        unsigned bit = 1u << i;
        if ((previous & bit) && !(next & bit))
            keyboard_release(xroar.keyboard_interface, keys[i]);
        if (!(previous & bit) && (next & bit))
            keyboard_press(xroar.keyboard_interface, keys[i]);
    }
    previous = next;
    fprintf(stderr, "keyboard-sample %u %u\n", sample_number++, next);
}

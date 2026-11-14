/* coco.py test equipment, inserted into XRoar's src/xroar.c before
 * handle_trap(). Original code for the starter's instrumented XRoar.
 *
 * Keys: at every hit of the trap condition in COCO_KEYS_AT, read the next
 * line of COCO_KEYS (XRoar key names separated by spaces; an empty line holds
 * nothing). Keys that are newly held are pressed and keys no longer held are
 * released through XRoar's keyboard API, which drives the emulated keyboard
 * matrix the program scans. At the end of the script every key is released.
 * Nothing here writes RAM, CPU registers or PIA state.
 *
 * Checkpoint: when the snapshot named by COCO_CHECKPOINT is written, log the
 * emulated tick and tell the video hook to save the next complete frame.
 *
 * Log lines on stderr: COCO_KEYS,<step>,<tick>  COCO_KEYS_END,<steps>,<tick>
 * COCO_CHECKPOINT,<tick>,<ticks per second>
 */
void coco_video_checkpoint(void);

static const struct {
	const char *name;
	int scan;
} coco_key_names[] = {
	{ "0", DSCAN_0 }, { "1", DSCAN_1 }, { "2", DSCAN_2 }, { "3", DSCAN_3 },
	{ "4", DSCAN_4 }, { "5", DSCAN_5 }, { "6", DSCAN_6 }, { "7", DSCAN_7 },
	{ "8", DSCAN_8 }, { "9", DSCAN_9 },
	{ "a", DSCAN_A }, { "b", DSCAN_B }, { "c", DSCAN_C }, { "d", DSCAN_D },
	{ "e", DSCAN_E }, { "f", DSCAN_F }, { "g", DSCAN_G }, { "h", DSCAN_H },
	{ "i", DSCAN_I }, { "j", DSCAN_J }, { "k", DSCAN_K }, { "l", DSCAN_L },
	{ "m", DSCAN_M }, { "n", DSCAN_N }, { "o", DSCAN_O }, { "p", DSCAN_P },
	{ "q", DSCAN_Q }, { "r", DSCAN_R }, { "s", DSCAN_S }, { "t", DSCAN_T },
	{ "u", DSCAN_U }, { "v", DSCAN_V }, { "w", DSCAN_W }, { "x", DSCAN_X },
	{ "y", DSCAN_Y }, { "z", DSCAN_Z },
	{ "colon", DSCAN_COLON }, { "semicolon", DSCAN_SEMICOLON },
	{ "comma", DSCAN_COMMA }, { "minus", DSCAN_MINUS },
	{ "full_stop", DSCAN_FULL_STOP }, { "slash", DSCAN_SLASH }, { "at", DSCAN_AT },
	{ "up", DSCAN_UP }, { "down", DSCAN_DOWN }, { "left", DSCAN_LEFT },
	{ "right", DSCAN_RIGHT }, { "space", DSCAN_SPACE }, { "enter", DSCAN_ENTER },
	{ "clear", DSCAN_CLEAR }, { "break", DSCAN_BREAK }, { "shift", DSCAN_SHIFT },
};
#define COCO_KEY_COUNT (sizeof(coco_key_names) / sizeof(coco_key_names[0]))

static bool coco_keys_read(FILE *script, bool *next) {
	char line[1024];
	for (unsigned i = 0; i < COCO_KEY_COUNT; ++i)
		next[i] = false;
	if (!fgets(line, sizeof(line), script))
		return false;
	for (char *word = strtok(line, " \t\r\n"); word; word = strtok(NULL, " \t\r\n")) {
		unsigned i = 0;
		while (i < COCO_KEY_COUNT && strcmp(word, coco_key_names[i].name))
			++i;
		if (i == COCO_KEY_COUNT) {
			fprintf(stderr, "COCO_KEYS_UNKNOWN,%s\n", word);
			exit(2);
		}
		next[i] = true;
	}
	return true;
}

static void coco_keys_trap(const char *condition) {
	static FILE *script;
	static bool held[COCO_KEY_COUNT];
	static unsigned step;
	static bool finished;
	const char *match = getenv("COCO_KEYS_AT");
	const char *path = getenv("COCO_KEYS");
	if (finished || !match || !path || strcmp(condition, match))
		return;
	if (!script && !(script = fopen(path, "r"))) {
		perror(path);
		exit(2);
	}
	bool next[COCO_KEY_COUNT];
	finished = !coco_keys_read(script, next);
	for (unsigned i = 0; i < COCO_KEY_COUNT; ++i) {
		if (held[i] && !next[i])
			keyboard_release(xroar.keyboard_interface, coco_key_names[i].scan);
		if (!held[i] && next[i])
			keyboard_press(xroar.keyboard_interface, coco_key_names[i].scan);
		held[i] = next[i];
	}
	if (finished) {
		fprintf(stderr, "COCO_KEYS_END,%u,%u\n", step, (unsigned)event_current_tick);
		fclose(script);
	} else {
		fprintf(stderr, "COCO_KEYS,%u,%u\n", step++, (unsigned)event_current_tick);
	}
}

static void coco_snapshot_written(const char *path) {
	const char *checkpoint = getenv("COCO_CHECKPOINT");
	if (!checkpoint || strcmp(path, checkpoint))
		return;
	fprintf(stderr, "COCO_CHECKPOINT,%u,%u\n", (unsigned)event_current_tick,
	        (unsigned)EVENT_TICK_RATE);
	coco_video_checkpoint();
}

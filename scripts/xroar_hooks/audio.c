/* coco.py test equipment, inserted into XRoar's src/null/ao_null.c.
 * Original code for the starter's instrumented XRoar.
 *
 * The null audio module normally asks XRoar's mixer for no samples. This
 * gives the mixer a buffer in signed 16-bit little-endian mono instead, and
 * appends every completed buffer to the COCO_AUDIO path. The samples are the
 * mixer's own output (DAC, mux, single-bit sound and gain), before any host
 * audio driver. Nothing here generates or alters a sample. A final partly
 * filled buffer is not written.
 *
 * Log lines on stderr: COCO_AUDIO_START,<tick>,<rate>,<frames per buffer>
 * and COCO_AUDIO,<tick> after each buffer.
 */
#define COCO_AUDIO_RATE 44100
#define COCO_AUDIO_FRAMES 1024

static int16_t coco_audio_buffer[COCO_AUDIO_FRAMES];
static FILE *coco_audio_file;

static void coco_audio_open(void) {
	const char *path = getenv("COCO_AUDIO");
	if (!path)
		return;
	if (!(coco_audio_file = fopen(path, "wb"))) {
		perror(path);
		exit(2);
	}
	fprintf(stderr, "COCO_AUDIO_START,%u,%d,%d\n", (unsigned)event_current_tick,
	        COCO_AUDIO_RATE, COCO_AUDIO_FRAMES);
}

static void coco_audio_write(const void *buffer) {
	if (!coco_audio_file)
		return;
	if (!buffer || fwrite(buffer, sizeof(int16_t), COCO_AUDIO_FRAMES, coco_audio_file)
	                   != COCO_AUDIO_FRAMES || fflush(coco_audio_file))
		exit(2);
	fprintf(stderr, "COCO_AUDIO,%u\n", (unsigned)event_current_tick);
}

static void coco_audio_close(void) {
	if (coco_audio_file && fclose(coco_audio_file))
		exit(2);
	coco_audio_file = NULL;
}

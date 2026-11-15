"""Original private output-callback instrumentation for pinned XRoar 1.12.1.

The sound lab is closed: its evidence is in examples/sound-slots and examples/timer-sound
(`scripts/coco.py check`, which records the mixer with the instrumented XRoar). This file
remains only because experiments/collect-room-output imports it. Delete this folder when
that experiment closes.
"""

import hashlib

PRISTINE = "e9fa06289dab8a8d025c21d38c0cc2c6c2b44cd7248443197aad6af83ece124f"


def instrument(source: bytes) -> bytes:
    if hashlib.sha256(source).hexdigest() != PRISTINE:
        raise ValueError("Expected pristine XRoar 1.12.1 ao_null.c")
    text = source.decode().replace("#include <stdlib.h>", "#include <stdlib.h>\n#include <stdio.h>")
    text = text.replace(
        "static void *new(void *cfg);",
        """static int16_t capture_buffer[1024];
static FILE *capture_file;
static void *new(void *cfg);""",
    )
    text = text.replace(
        "sound_interface_new(NULL, SOUND_FMT_NULL, 44100, 1, 1024)",
        "sound_interface_new(capture_buffer, SOUND_FMT_S16_LE, 44100, 1, 1024)",
    )
    text = text.replace(
        "\t(void)cfg;",
        """\t(void)cfg;
    const char *path = getenv("AUDIO_CAPTURE");
    if (!path || !(capture_file = fopen(path, "wb"))) exit(2);""",
    )
    text = text.replace(
        "\tfree(aonull);\n}", "\tif (fclose(capture_file)) exit(2);\n\tfree(aonull);\n}"
    )
    needle = "static void *ao_null_write_buffer(void *sptr, void *buffer) {"
    text = text.replace(
        needle,
        needle
        + """
    if (!buffer || fwrite(buffer, 2, 1024, capture_file) != 1024) exit(2);
    if (fflush(capture_file)) exit(2);
    fprintf(stderr, "PCM,%u,1024\\n", (unsigned)event_current_tick);
""",
    )
    text = text.replace(
        "\taonull->last_pause_cycle = event_current_tick;",
        '    fprintf(stderr, "AUDIO_START,%u\\n", (unsigned)event_current_tick);\n'
        "\taonull->last_pause_cycle = event_current_tick;",
        1,
    )
    text = text.replace(
        "\tsound_interface_free(aonull->public.sound_interface);",
        '    fprintf(stderr, "AUDIO_END,%u\\n", (unsigned)event_current_tick);\n'
        "\tsound_interface_free(aonull->public.sound_interface);",
    )
    return text.encode()

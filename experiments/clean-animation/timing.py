"""Check publication/reuse against independently specified XRoar field boundaries."""


def publication_phases(groups: list[list[int]], renderer_ticks: list[int]) -> dict:
    """FS low spans 32 lines; draw callbacks occur at FS rise in this model."""
    publication_delays = []
    reuse_delays = []
    for _, _, published, reused in groups:
        rising = next((tick for tick in renderer_ticks if tick > published), None)
        if rising is None:
            raise ValueError("missing adoption boundary")
        publication_delay = published - (rising - 32 * 912)
        reuse_delay = reused - rising
        # Deliberately loose bounds allow polling/instruction latency, but not
        # another scanline (publication) or field (reuse). No silicon claim.
        if not 0 <= publication_delay < 912:
            raise ValueError("publication outside fresh falling-edge window")
        if not 0 <= reuse_delay < 912:
            raise ValueError("old screen reused before modeled adoption or too late")
        publication_delays.append(publication_delay)
        reuse_delays.append(reuse_delay)
    if not groups:
        raise ValueError("missing publication events")
    return {
        "publication_after_fs_fall_ticks": publication_delays,
        "reuse_after_fs_rise_ticks": reuse_delays,
    }

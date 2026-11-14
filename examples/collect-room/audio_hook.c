/* Read-only evidence at the real PIA output callback, not a synthetic waveform. */
    if (md->CPU->reg_pc >= 0x3000 && md->CPU->reg_pc < 0x7e00)
        fprintf(stderr, "DAC,%u,%04x,%02x,%02x,%02x,%02x,%02x,%02x\n",
                (unsigned)event_current_tick, md->CPU->reg_pc,
                PIA_VALUE_A(md->PIA1), md->PIA1->a.control_register,
                md->PIA1->a.direction_register,
                md->PIA0->a.control_register, md->PIA0->b.control_register,
                md->PIA1->b.control_register);

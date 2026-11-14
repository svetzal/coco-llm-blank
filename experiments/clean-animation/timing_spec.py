"""Expected phases come from the model contract, not measured averages."""

import pytest
from timing import publication_phases


class DescribePublicationPhases:
    def should_accept_bounded_publication_then_adoption(self):
        assert publication_phases([[0, 1, 1000, 30000]], [30000]) == {
            "publication_after_fs_fall_ticks": [184],
            "reuse_after_fs_rise_ticks": [0],
        }

    @pytest.mark.parametrize(
        "groups,ticks",
        [
            ([], []),
            ([[0, 1, 1000, 30000]], []),
            ([[0, 1, 1000, 29999]], [30000]),
            ([[0, 1, 1000, 31000]], [30000]),
            ([[0, 1, 500, 30000]], [30000]),
            ([[0, 1, 2000, 30000]], [30000]),
        ],
    )
    def should_reject_stale_or_late_publication_and_premature_reuse(self, groups, ticks):
        with pytest.raises(ValueError):
            publication_phases(groups, ticks)

"""art.py turns contracts and image specs into prompts, and spends money only with --spend."""

import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest
from art import (
    MAXIMUM_REFERENCES,
    SPEND_NOTICE,
    GeneratedImage,
    ImageService,
    ImageServiceError,
    Runtime,
    SpecError,
    background_arguments,
    build_prompt,
    image_document,
    load,
    main,
    merge,
    plan_images,
    resolve,
)
from PIL import Image


def png_bytes(mode: str) -> bytes:
    buffer = io.BytesIO()
    Image.new(mode, (2, 2)).save(buffer, "PNG")
    return buffer.getvalue()


PNG = png_bytes("RGB")
TRANSPARENT_PNG = png_bytes("RGBA")
SAMPLE = b"\x89PNG approved sample"
CREATED = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
KEY = "sk-test-secret"

CONTRACT = {
    "Name": "Cave Run",
    "VisualLanguage": {"genre": "cave platformer"},
    "Palette": {
        "colours": [
            {"name": "black", "hex": "#000000", "use": "background"},
            {"name": "green", "hex": "#00ff00"},
            {"name": "white", "hex": "#ffffff"},
        ],
        "rules": ["green is for the player"],
    },
    "Target": {
        "machine": "CoCo 3",
        "mode": "gime-320x16",
        "grid": {"width": 160, "height": 96},
        "pixel_aspect": 2,
        "background": "black",
    },
    "CompositionPolicy": {"sprite": "One centred figure.", "screen": "A full scene."},
    "Constraints": {"must_not": ["no text"]},
}

SPRITE = {
    "Contract": "game.contract.json",
    "Role": "sprite",
    "Subject": {"name": "Miner", "description": "a miner with a lamp", "hat": "yellow"},
    "Context": {"why": "the player sprite"},
}

SET = {
    "Contract": "../game.contract.json",
    "Role": "sprite",
    "Target": {"background": "transparent"},
    "Items": [
        {"slug": "miner", "name": "Miner", "reference": "refs/miner.png"},
        {"slug": "bat", "name": "Bat"},
    ],
    "Variants": [{"slug": "idle", "name": "idle"}, {"slug": "run", "name": "running"}],
}


def write_json(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return path


@pytest.fixture
def contract(tmp_path: Path) -> Path:
    return write_json(tmp_path / "game.contract.json", CONTRACT)


@pytest.fixture
def sprite(tmp_path: Path, contract: Path) -> Path:
    return write_json(tmp_path / "miner.spec.json", SPRITE)


@pytest.fixture
def sample(tmp_path: Path) -> Path:
    path = tmp_path / "samples" / "approved.png"
    path.parent.mkdir()
    path.write_bytes(SAMPLE)
    return path


@pytest.fixture
def set_spec(tmp_path: Path, contract: Path) -> Path:
    spec = write_json(tmp_path / "sets" / "cast.spec.json", SET)
    (spec.parent / "refs").mkdir()
    (spec.parent / "refs" / "miner.png").write_bytes(b"\x89PNG miner")
    return spec


@pytest.fixture
def service() -> Mock:
    gateway = Mock(spec=ImageService)
    gateway.generate.return_value = GeneratedImage(png=PNG, revised_prompt="revised")
    gateway.edit.return_value = GeneratedImage(png=TRANSPARENT_PNG)
    return gateway


@pytest.fixture
def opened_keys() -> list[str]:
    return []


@pytest.fixture
def runtime(service: Mock, opened_keys: list[str]) -> Runtime:
    def open_service(key: str) -> Mock:
        opened_keys.append(key)
        return service

    return Runtime(environ={"OPENAI_API_KEY": KEY}, open_service=open_service, now=lambda: CREATED)


def json_section(prompt: str) -> dict:
    return json.loads(prompt[prompt.index("\n{\n") + 1 :])


class DescribeMerge:
    def should_let_a_later_scalar_win(self) -> None:
        assert merge({"a": 1, "b": 2}, {"b": 3}, "late", {}) == {"a": 1, "b": 3}

    def should_merge_objects_recursively(self) -> None:
        base = {"Target": {"machine": "CoCo 3", "grid": {"width": 160, "height": 96}}}

        merged = merge(base, {"Target": {"grid": {"width": 320}}}, "late", {})

        assert merged == {"Target": {"machine": "CoCo 3", "grid": {"width": 320, "height": 96}}}

    def should_replace_lists_rather_than_concatenate_them(self) -> None:
        base = {"Constraints": {"must": ["a", "b"]}}

        merged = merge(base, {"Constraints": {"must": ["c"]}}, "late", {})

        assert merged == {"Constraints": {"must": ["c"]}}

    def should_append_with_a_plus_key(self) -> None:
        base = {"Constraints": {"must_not": ["no text"]}}

        merged = merge(base, {"Constraints": {"must_not+": ["no floor"]}}, "late", {})

        assert merged == {"Constraints": {"must_not": ["no text", "no floor"]}}

    def should_append_to_nothing_as_to_an_empty_list(self) -> None:
        assert merge({}, {"Constraints": {"must+": ["x"]}}, "only", {}) == {
            "Constraints": {"must": ["x"]}
        }

    def should_replace_a_scalar_with_an_object(self) -> None:
        assert merge({"Style": "flat"}, {"Style": {"outline": "thin"}}, "late", {}) == {
            "Style": {"outline": "thin"}
        }

    def should_record_which_layer_set_each_key(self) -> None:
        origins: dict = {}

        merge({}, {"Target": {"mode": "x"}}, "a.json", origins)
        merge({}, {"Target": {"grid": {"width": 1}}}, "b.json", origins)

        assert origins[("Target", "mode")] == "a.json"
        assert origins[("Target", "grid", "width")] == "b.json"

    def should_name_the_layer_and_key_of_a_bad_append(self) -> None:
        with pytest.raises(SpecError, match=r"b\.json: Constraints\.must\+: .* must be a list"):
            merge({}, {"Constraints": {"must+": "x"}}, "b.json", {})

    def should_refuse_to_append_to_a_value_that_is_not_a_list(self) -> None:
        with pytest.raises(SpecError, match=r"b\.json: Style\+: the earlier value is not a list"):
            merge({"Style": "flat"}, {"Style+": ["x"]}, "b.json", {})


class DescribeValidation:
    def should_name_the_layer_and_key_that_broke_the_spec(self) -> None:
        bad = {"Target": {"grid": {"width": 0}}}

        with pytest.raises(SpecError) as raised:
            resolve([("contract.json", CONTRACT), ("bad.json", bad), ("sprite.json", SPRITE)])

        assert "bad.json: Target.grid.width: Input should be greater than 0" in str(raised.value)

    def should_name_a_subject_key_without_the_shape_tag(self) -> None:
        bad = SPRITE | {"Subject": {"description": "no name"}}

        with pytest.raises(SpecError, match=r"bad\.json: Subject\.name: Field required"):
            resolve([("contract.json", CONTRACT), ("bad.json", bad)])

    def should_say_when_no_layer_gave_a_required_section(self) -> None:
        with pytest.raises(SpecError, match=r"\(no layer\): Role: Field required"):
            resolve([("contract.json", CONTRACT)])

    def should_reject_an_unknown_section(self) -> None:
        with pytest.raises(SpecError, match=r"typo\.json: Stlye: Extra inputs"):
            resolve([("c.json", CONTRACT), ("s.json", SPRITE), ("typo.json", {"Stlye": {}})])

    def should_accept_free_form_detail_in_open_sections(self) -> None:
        spec = resolve([("c.json", CONTRACT), ("s.json", SPRITE)])

        assert spec.document()["Subject"]["hat"] == "yellow"

    def should_require_a_background_from_the_palette(self) -> None:
        bad = {"Target": {"background": "purple"}}

        with pytest.raises(SpecError, match=r"bad\.json: Target: .*'purple' is not a palette"):
            resolve([("c.json", CONTRACT), ("s.json", SPRITE), ("bad.json", bad)])

    def should_accept_a_background_given_by_hex(self) -> None:
        layer = {"Target": {"background": "#FFFFFF"}}

        spec = resolve([("c.json", CONTRACT), ("s.json", SPRITE), ("hex.json", layer)])

        assert spec.background() == "white (#FFFFFF)"

    def should_refuse_more_subjects_than_cells(self) -> None:
        sheet = {
            "Role": "sprite-sheet",
            "Canvas": {"cells": {"columns": 1, "rows": 1}},
            "Subject": [{"name": "a"}, {"name": "b"}],
        }

        with pytest.raises(SpecError, match="2 subjects do not fit in 1 cells"):
            resolve([("c.json", CONTRACT), ("sheet.json", sheet)])

    @pytest.mark.parametrize(
        ("layer", "message"),
        [
            ({"Items": [{"slug": "a", "name": "A"}]}, "Subject for one image or Items"),
            ({"Subject": None, "Variants": [{"slug": "a", "name": "A"}]}, "Variants need Items"),
            (
                {
                    "Subject": None,
                    "Items": [{"slug": "a", "name": "A"}, {"slug": "a", "name": "B"}],
                },
                "repeated: a",
            ),
            ({"Subject": None, "Items": [{"slug": "Bad Slug", "name": "A"}]}, "should match"),
            (
                {
                    "Subject": None,
                    "Items": [{"slug": "a", "name": "A"}],
                    "Output": {"pattern": "x.png"},
                },
                r"exactly \{slug\}",
            ),
            (
                {
                    "Subject": None,
                    "Items": [{"slug": "a", "name": "A"}],
                    "Output": {"pattern": "{slug}"},
                },
                "end with .png",
            ),
        ],
    )
    def should_check_set_specs(self, layer: dict, message: str) -> None:
        with pytest.raises(SpecError, match=message):
            resolve([("c.json", CONTRACT), ("s.json", SPRITE), ("set.json", layer)])

    def should_need_something_to_draw(self) -> None:
        with pytest.raises(SpecError, match="needs Subject"):
            resolve([("c.json", CONTRACT), ("role.json", {"Role": "screen"})])


class DescribeLoading:
    def should_merge_the_contract_under_the_spec(self, sprite: Path, contract: Path) -> None:
        loaded = load([sprite])

        assert loaded.contract == contract
        assert loaded.spec.target.machine == "CoCo 3"
        assert "Contract" not in loaded.spec.document()

    def should_resolve_paths_relative_to_the_file_that_names_them(
        self, tmp_path: Path, set_spec: Path
    ) -> None:
        write_json(
            tmp_path / "game.contract.json",
            CONTRACT | {"ApprovedSamples": [{"file": "samples/approved.png", "use": "outline"}]},
        )

        spec = load([set_spec]).spec

        assert spec.samples[0].file == tmp_path / "samples" / "approved.png"
        assert spec.items[0].reference == set_spec.parent / "refs" / "miner.png"

    def should_let_a_later_layer_add_constraints(self, tmp_path: Path, sprite: Path) -> None:
        extra = write_json(tmp_path / "extra.json", {"Constraints": {"must_not+": ["no floor"]}})

        spec = load([sprite, extra]).spec

        assert spec.constraints.must_not == ["no text", "no floor"]

    @pytest.mark.parametrize(
        ("content", "message"),
        [("{not json", "not valid JSON"), ("[1, 2]", "a layer must be a JSON object")],
    )
    def should_name_a_file_that_is_not_a_layer(
        self, tmp_path: Path, content: str, message: str
    ) -> None:
        path = tmp_path / "broken.json"
        path.write_text(content)

        with pytest.raises(SpecError, match=f"broken.json: {message}"):
            load([path])

    def should_name_a_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(SpecError, match="absent.json: cannot read"):
            load([tmp_path / "absent.json"])

    def should_need_the_contract_to_be_a_path(self, tmp_path: Path) -> None:
        spec = write_json(tmp_path / "s.json", SPRITE | {"Contract": 3})

        with pytest.raises(SpecError, match="s.json: Contract: must be a path"):
            load([spec])


class DescribeThePrompt:
    @pytest.fixture
    def spec(self):
        return resolve([("c.json", CONTRACT), ("s.json", SPRITE)])

    def should_state_the_reduction_from_the_target(self, spec) -> None:
        prompt = build_prompt(spec, plan_images(spec, Path("miner.png"))[0])

        assert "a 160x96 grid of target pixels (gime-320x16)" in prompt
        assert "each target pixel is 2:1, width to height" in prompt
        assert "these 3 colours" in prompt
        assert "black (#000000), green (#00FF00), white (#FFFFFF)" in prompt
        assert "at least 3 target pixels across: at least 1.9%" in prompt
        assert "and 3.1% of the image height" in prompt
        assert "The background is black (#000000)." in prompt
        assert "Context section" in prompt
        assert "Do not draw text" in prompt

    def should_end_with_the_whole_image_document(self, spec) -> None:
        image = plan_images(spec, Path("miner.png"))[0]

        prompt = build_prompt(spec, image)

        assert json_section(prompt) == image.document
        assert prompt.endswith(json.dumps(image.document, indent=2))
        document = json_section(prompt)
        assert document["Context"] == {"why": "the player sprite"}
        assert document["Palette"]["rules"] == ["green is for the player"]
        assert document["Subject"]["hat"] == "yellow"

    def should_show_only_the_composition_policy_for_the_role(self, spec) -> None:
        assert image_document(spec)["CompositionPolicy"] == {"sprite": "One centred figure."}

    def should_ask_for_a_fully_transparent_background(self) -> None:
        layer = {"Target": {"background": "transparent"}}
        spec = resolve([("c.json", CONTRACT), ("s.json", SPRITE), ("clear.json", layer)])

        prompt = build_prompt(spec, plan_images(spec, Path("miner.png"))[0])

        assert "The background must be fully transparent." in prompt
        assert "no semi-transparent glow, shadow or fringe" in prompt
        assert "generous padding" in prompt
        assert "The background is black" not in prompt

    def should_explain_each_reference_image_in_order(self, sample: Path) -> None:
        layer = SPRITE | {"ApprovedSamples": [{"file": str(sample), "use": "outline weight"}]}
        spec = resolve([("c.json", CONTRACT), ("s.json", layer)])
        image = plan_images(spec, Path("miner.png"), [Path("miner-ref.png")])[0]

        prompt = build_prompt(spec, image)

        assert image.references == [sample, Path("miner-ref.png")]
        assert "1. An approved style sample. Match its style (outline weight)" in prompt
        assert "2. The subject. Keep its appearance" in prompt
        assert "not from the reference images" in prompt

    def should_say_nothing_about_references_without_them(self, spec) -> None:
        prompt = build_prompt(spec, plan_images(spec, Path("miner.png"))[0])

        assert "reference" not in prompt


class DescribeSets:
    def should_plan_one_image_per_item_and_variant(self, set_spec: Path, tmp_path: Path) -> None:
        spec = load([set_spec]).spec

        images = plan_images(spec, tmp_path / "out")

        assert [image.path.name for image in images] == [
            "miner-idle.png",
            "miner-run.png",
            "bat-idle.png",
            "bat-run.png",
        ]
        assert images[1].document["Subject"] == {"name": "Miner"}
        assert images[1].document["Variant"] == {"name": "running"}
        assert "Items" not in images[1].document
        assert images[0].subject_references == [set_spec.parent / "refs" / "miner.png"]
        assert images[2].subject_references == []

    def should_use_the_output_pattern(self, tmp_path: Path) -> None:
        layer = {
            "Subject": None,
            "Items": [{"slug": "a", "name": "A"}],
            "Output": {"pattern": "sprite-{slug}.png"},
        }
        spec = resolve([("c.json", CONTRACT), ("s.json", SPRITE), ("set.json", layer)])

        assert plan_images(spec, tmp_path)[0].path == tmp_path / "sprite-a.png"

    def should_need_a_directory_for_a_set_and_a_png_for_one_image(self, set_spec, sprite) -> None:
        with pytest.raises(SpecError, match="needs an output directory"):
            plan_images(load([set_spec]).spec, Path("out.png"))
        with pytest.raises(SpecError, match="needs a .png output file"):
            plan_images(load([sprite]).spec, Path("out"))

    def should_print_every_prompt_or_only_the_chosen_ones(self, set_spec, capsys) -> None:
        assert main(["prompt", str(set_spec), "--only", "run"]) == 0

        output = capsys.readouterr().out
        assert "=== miner-run.png ===" in output
        assert "=== bat-run.png ===" in output
        assert "idle" not in output


class DescribeGenerate:
    def should_spend_nothing_without_the_spend_flag(
        self, sprite: Path, tmp_path: Path, runtime: Runtime, service: Mock, capsys
    ) -> None:
        out = tmp_path / "art" / "miner.png"

        status = main(["generate", str(sprite), "--out", str(out)], runtime)

        assert status == 2
        assert service.generate.call_count == 0
        assert service.edit.call_count == 0
        assert not out.exists()
        output = capsys.readouterr().out
        assert "Model: gpt-image-2.5-sunburst" in output
        assert f"make: {out}" in output
        assert "Images to make: 1" in output
        assert SPEND_NOTICE in output

    def should_write_the_image_its_record_and_a_manifest_line(
        self, sprite: Path, tmp_path: Path, runtime: Runtime, service: Mock, opened_keys
    ) -> None:
        out = tmp_path / "art" / "miner.png"

        status = main(
            ["generate", str(sprite), "--out", str(out), "--spend", "--size", "1024x1024"],
            runtime,
        )

        assert status == 0
        assert opened_keys == [KEY]
        call = service.generate.call_args.kwargs
        assert call["model"] == "gpt-image-2.5-sunburst"
        assert call["size"] == "1024x1024"
        assert call["quality"] == "auto"
        assert out.read_bytes() == PNG
        record = json.loads(out.with_suffix(".json").read_text())
        assert record["prompt"] == call["prompt"]
        assert record["revised_prompt"] == "revised"
        assert record["created"] == "2026-11-16T12:00:00+00:00"
        assert record["contract"] == str(tmp_path / "game.contract.json")
        assert record["image_sha256"] == hashlib.sha256(PNG).hexdigest()
        assert record["spec"]["Subject"]["name"] == "Miner"
        line = json.loads((out.parent / "manifest.jsonl").read_text())
        assert line["path"] == str(out)
        assert line["prompt_sha256"] == hashlib.sha256(call["prompt"].encode()).hexdigest()

    def should_send_samples_and_references_to_the_edit_endpoint(
        self, tmp_path: Path, contract: Path, sample: Path, runtime: Runtime, service: Mock
    ) -> None:
        spec = write_json(
            tmp_path / "s.json",
            SPRITE | {"ApprovedSamples": [{"file": "samples/approved.png", "use": "style"}]},
        )
        reference = tmp_path / "miner-ref.png"
        reference.write_bytes(b"\x89PNG reference")
        out = tmp_path / "miner.png"

        main(
            ["generate", str(spec), "--out", str(out), "--spend", "--reference", str(reference)],
            runtime,
        )

        assert service.generate.call_count == 0
        assert service.edit.call_args.kwargs["references"] == [sample, reference]
        record = json.loads(out.with_suffix(".json").read_text())
        assert record["references"] == [
            {"path": str(sample), "sha256": hashlib.sha256(SAMPLE).hexdigest()},
            {"path": str(reference), "sha256": hashlib.sha256(b"\x89PNG reference").hexdigest()},
        ]

    def should_need_the_api_key_and_never_show_it(
        self, sprite: Path, tmp_path: Path, runtime: Runtime, service: Mock, capsys
    ) -> None:
        keyless = runtime.model_copy(update={"environ": {}})

        status = main(
            ["generate", str(sprite), "--out", str(tmp_path / "m.png"), "--spend"], keyless
        )

        assert status == 1
        assert "OPENAI_API_KEY is not set" in capsys.readouterr().err
        assert service.generate.call_count == 0

    def should_skip_an_existing_image_unless_forced(
        self, sprite: Path, tmp_path: Path, runtime: Runtime, service: Mock, capsys
    ) -> None:
        out = tmp_path / "miner.png"
        out.write_bytes(b"keep me")

        skipped = main(["generate", str(sprite), "--out", str(out), "--spend"], runtime)

        assert skipped == 0
        assert out.read_bytes() == b"keep me"
        assert "skip (exists)" in capsys.readouterr().out
        assert service.generate.call_count == 0
        forced = main(["generate", str(sprite), "--out", str(out), "--spend", "--force"], runtime)
        assert forced == 0
        assert out.read_bytes() == PNG

    def should_resume_a_set_and_make_only_the_missing_images(
        self, set_spec: Path, tmp_path: Path, runtime: Runtime, service: Mock
    ) -> None:
        out = tmp_path / "cast"
        out.mkdir()
        (out / "miner-idle.png").write_bytes(b"done")

        status = main(
            ["generate", str(set_spec), "--out", str(out), "--spend", "--only", "miner"], runtime
        )

        assert status == 0
        assert service.edit.call_count == 1
        assert (out / "miner-idle.png").read_bytes() == b"done"
        assert (out / "miner-run.png").read_bytes() == TRANSPARENT_PNG
        lines = (out / "manifest.jsonl").read_text().splitlines()
        assert [json.loads(line)["variant"] for line in lines] == ["run"]

    def should_report_an_api_failure_without_a_traceback_or_the_key(
        self, sprite: Path, tmp_path: Path, runtime: Runtime, service: Mock, capsys
    ) -> None:
        service.generate.side_effect = ImageServiceError(f"Incorrect API key provided: {KEY}")
        out = tmp_path / "miner.png"

        status = main(["generate", str(sprite), "--out", str(out), "--spend"], runtime)

        assert status == 1
        error = capsys.readouterr().err
        assert "the image API failed: Incorrect API key provided: [OPENAI_API_KEY]" in error
        assert KEY not in error
        assert "Traceback" not in error
        assert not out.exists()

    def should_refuse_more_references_than_the_api_accepts(
        self, sprite: Path, tmp_path: Path, runtime: Runtime, capsys
    ) -> None:
        references = []
        for number in range(MAXIMUM_REFERENCES + 1):
            reference = tmp_path / f"ref-{number}.png"
            reference.write_bytes(b"x")
            references += ["--reference", str(reference)]

        status = main(["generate", str(sprite), "--out", str(tmp_path / "m.png"), *references])

        assert status == 1
        assert "17 reference images; the API accepts at most 16" in capsys.readouterr().err

    def should_refuse_a_reference_that_is_not_an_image_file(
        self, sprite: Path, tmp_path: Path, capsys
    ) -> None:
        reference = tmp_path / "notes.txt"
        reference.write_text("x")

        status = main(
            [
                "generate",
                str(sprite),
                "--out",
                str(tmp_path / "m.png"),
                "--reference",
                str(reference),
            ]
        )

        assert status == 1
        assert "must be PNG, JPEG or WebP" in capsys.readouterr().err

    def should_name_a_missing_reference(self, sprite: Path, tmp_path: Path, capsys) -> None:
        missing = tmp_path / "missing.png"

        status = main(
            ["generate", str(sprite), "--out", str(tmp_path / "m.png"), "--reference", str(missing)]
        )

        assert status == 1
        assert "missing.png: cannot read the reference image" in capsys.readouterr().err

    def should_refuse_a_prompt_longer_than_the_api_accepts(
        self, tmp_path: Path, contract: Path, capsys
    ) -> None:
        long = SPRITE | {"Subject": {"name": "Miner", "description": "x" * 33000}}
        spec = write_json(tmp_path / "long.json", long)

        status = main(["generate", str(spec), "--out", str(tmp_path / "m.png")])

        assert status == 1
        assert "the API accepts at most 32000" in capsys.readouterr().err

    def should_name_an_only_that_matches_nothing(self, set_spec: Path, tmp_path: Path, capsys):
        status = main(["generate", str(set_spec), "--out", str(tmp_path), "--only", "dragon"])

        assert status == 1
        assert "--only dragon matches no image" in capsys.readouterr().err


class DescribeTransparency:
    @pytest.fixture
    def clear_sprite(self, tmp_path: Path, contract: Path) -> Path:
        return write_json(
            tmp_path / "clear.spec.json", SPRITE | {"Target": {"background": "transparent"}}
        )

    def should_ask_the_api_for_a_transparent_png(self) -> None:
        assert background_arguments(True) == {"background": "transparent", "output_format": "png"}
        assert background_arguments(False) == {}

    def should_request_transparency_and_record_the_alpha_channel(
        self, clear_sprite: Path, tmp_path: Path, runtime: Runtime, service: Mock, capsys
    ) -> None:
        service.generate.return_value = GeneratedImage(png=TRANSPARENT_PNG)
        out = tmp_path / "miner.png"

        status = main(["generate", str(clear_sprite), "--out", str(out), "--spend"], runtime)

        assert status == 0
        assert service.generate.call_args.kwargs["transparent"] is True
        assert "Background: transparent" in capsys.readouterr().out
        record = json.loads(out.with_suffix(".json").read_text())
        assert record["background"] == "transparent"
        assert record["has_alpha"] is True
        with Image.open(out) as image:
            assert image.mode == "RGBA"

    def should_fail_when_the_returned_png_has_no_alpha_channel(
        self, clear_sprite: Path, tmp_path: Path, runtime: Runtime, service: Mock, capsys
    ) -> None:
        out = tmp_path / "miner.png"

        status = main(["generate", str(clear_sprite), "--out", str(out), "--spend"], runtime)

        assert status == 1
        assert "miner.png has no alpha channel" in capsys.readouterr().err
        assert out.exists()
        assert json.loads(out.with_suffix(".json").read_text())["has_alpha"] is False

    def should_treat_bytes_that_are_not_a_png_as_having_no_alpha(
        self, clear_sprite: Path, tmp_path: Path, runtime: Runtime, service: Mock
    ) -> None:
        service.generate.return_value = GeneratedImage(png=b"not a png")
        out = tmp_path / "miner.png"

        assert main(["generate", str(clear_sprite), "--out", str(out), "--spend"], runtime) == 1

    def should_ask_for_an_opaque_image_with_a_palette_background(
        self, sprite: Path, tmp_path: Path, runtime: Runtime, service: Mock
    ) -> None:
        out = tmp_path / "miner.png"

        main(["generate", str(sprite), "--out", str(out), "--spend"], runtime)

        assert service.generate.call_args.kwargs["transparent"] is False
        record = json.loads(out.with_suffix(".json").read_text())
        assert record["background"] == "black (#000000)"
        assert record["has_alpha"] is False


class DescribeModelChoice:
    @pytest.mark.parametrize(
        ("choice", "model"),
        [
            ([], "gpt-image-2.5-sunburst"),
            (["--model", "sunburst"], "gpt-image-2.5-sunburst"),
            (["--model", "flare"], "gpt-image-2.5-flare"),
            (["--model", "gpt-image-2.6-sunburst"], "gpt-image-2.6-sunburst"),
        ],
    )
    def should_resolve_an_alias_to_the_full_model_id(
        self, sprite: Path, tmp_path: Path, runtime: Runtime, service: Mock, choice, model
    ) -> None:
        out = tmp_path / "miner.png"

        main(["generate", str(sprite), "--out", str(out), "--spend", *choice], runtime)

        assert service.generate.call_args.kwargs["model"] == model
        assert json.loads(out.with_suffix(".json").read_text())["model"] == model
        assert json.loads((tmp_path / "manifest.jsonl").read_text())["model"] == model

    def should_show_both_aliases_in_the_help(self, capsys) -> None:
        with pytest.raises(SystemExit):
            main(["generate", "--help"])

        help_text = " ".join(capsys.readouterr().out.split())
        assert "sunburst (gpt-image-2.5-sunburst: high quality, the default)" in help_text
        assert "flare (gpt-image-2.5-flare: lower quality, cheaper)" in help_text


class DescribeComposeAndSchema:
    def should_write_the_resolved_spec(self, sprite: Path, tmp_path: Path) -> None:
        out = tmp_path / "build" / "resolved.json"

        assert main(["compose", str(sprite), "-o", str(out)]) == 0

        resolved = json.loads(out.read_text())
        assert resolved["Target"]["grid"] == {"width": 160, "height": 96}
        assert resolved["Subject"]["name"] == "Miner"

    def should_print_the_resolved_spec_without_an_output(self, sprite: Path, capsys) -> None:
        assert main(["compose", str(sprite)]) == 0

        assert json.loads(capsys.readouterr().out)["Role"] == "sprite"

    def should_print_the_prompt_for_one_image(self, sprite: Path, capsys) -> None:
        assert main(["prompt", str(sprite)]) == 0

        assert "160x96 grid" in capsys.readouterr().out

    def should_report_a_bad_layer_and_fail(self, tmp_path: Path, capsys) -> None:
        assert main(["compose", str(tmp_path / "absent.json")]) == 1

        assert "FAIL:" in capsys.readouterr().err

    def should_print_a_json_schema_of_the_spec(self, capsys) -> None:
        assert main(["schema"]) == 0

        schema = json.loads(capsys.readouterr().out)
        assert {"Target", "Palette", "Role", "Items", "Canvas"} <= set(schema["properties"])

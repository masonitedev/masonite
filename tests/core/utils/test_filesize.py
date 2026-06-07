import pytest

from src.masonite.utils.filesize import format_human_size, parse_human_size


class TestParseHumanSize:
    def test_parses_integers_as_bytes(self):
        assert parse_human_size(10) == 10
        assert parse_human_size(0) == 0
        # False is the validator default for "no size limit"
        assert parse_human_size(False) == 0

    def test_parses_plain_numeric_strings(self):
        assert parse_human_size("10") == 10

    def test_parses_binary_units_case_insensitively(self):
        assert parse_human_size("2MB") == 2 * 1024**2
        assert parse_human_size("2mb") == 2 * 1024**2
        assert parse_human_size("4K") == 4 * 1024
        assert parse_human_size("4k") == 4 * 1024
        assert parse_human_size("1GB") == 1024**3

    def test_parses_iec_and_verbose_units(self):
        assert parse_human_size("512KiB") == 512 * 1024
        assert parse_human_size("3 megabytes") == 3 * 1024**2
        assert parse_human_size("1 kilobyte") == 1024

    def test_parses_byte_units(self):
        assert parse_human_size("100b") == 100
        assert parse_human_size("100 bytes") == 100

    def test_allows_whitespace_between_size_and_unit(self):
        assert parse_human_size("2 MB") == 2 * 1024**2

    def test_rejects_unknown_units(self):
        with pytest.raises(ValueError):
            parse_human_size("2 lightyears")

    def test_rejects_non_numeric_sizes(self):
        with pytest.raises(ValueError):
            parse_human_size("MB")
        with pytest.raises(ValueError):
            parse_human_size(2.5)


class TestFormatHumanSize:
    def test_formats_exact_multiples_without_decimals(self):
        assert format_human_size(2 * 1024**2) == "2 MB"
        assert format_human_size(4 * 1024) == "4 KB"

    def test_formats_fractions_with_two_decimals(self):
        assert format_human_size(1536) == "1.50 KB"

    def test_formats_bytes_with_pluralization(self):
        assert format_human_size(0) == "0 bytes"
        assert format_human_size(1) == "1 byte"
        assert format_human_size(100) == "100 bytes"

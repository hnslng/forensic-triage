from forensic_triage.filesystem import parse_fls
from forensic_triage.partitions import parse_mmls


def test_parse_mmls_uses_dynamic_offsets():
    output = """DOS Partition Table
Units are in 512-byte sectors

      Slot      Start        End          Length       Description
000:  Meta      0000000000   0000000000   0000000001   Primary Table (#0)
001:  -------   0000000000   0000004095   0000004096   Unallocated
002:  Meta      0000000001   0000000001   0000000001   GPT Header
003:  000:000   0000004096   0000100000   0000095905   NTFS / exFAT (0x07)
"""
    rows = parse_mmls(output)
    assert rows[-1]["start_sector"] == 4096
    assert rows[-1]["allocated"] is True
    assert rows[0]["allocated"] is False
    assert rows[-2]["allocated"] is False


def test_parse_fls_bodyfile():
    output = """0|/docs/report.PDF|12-128-1|r/rrwxrwxrwx|0|0|1234|1|2|3|4
0|/docs|10-144-1|d/drwxrwxrwx|0|0|0|1|2|3|4
"""
    files, directories = parse_fls(output, "002")
    assert files[0]["path"] == "docs/report.PDF"
    assert files[0]["size"] == 1234
    assert files[0]["original_extension"] == "PDF"
    assert files[0]["category"] == "Dokumente"
    assert directories[0]["path"] == "docs"


def test_parse_fls_allows_pipe_in_filename():
    output = "0|/docs/a|b.txt|9|r/rrwxrwxrwx|0|0|12|1|2|3|4\n"
    files, _ = parse_fls(output, "002")
    assert files[0]["path"] == "docs/a|b.txt"


def test_parse_fls_excludes_deleted_entries():
    output = """0|/$OrphanFiles/old.pdf (deleted)|9|r/rrwxrwxrwx|0|0|12|1|2|3|4
0|/$OrphanFiles/old.pdf|10|r/rrwxrwxrwx|0|0|12|1|2|3|4
0|/$ALLOC_BITMAP|11|r/r--x--x--x|0|0|117353|1|2|3|4
0|/$MBR|12|v/v---------|0|0|512|1|2|3|4
"""
    files, directories = parse_fls(output, "002")
    assert files == []
    assert directories == []

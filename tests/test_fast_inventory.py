from forensic_triage.fast_inventory import find_partition_path, inventory_tree


def test_find_partition_path_uses_dynamic_start_sector():
    data = {
        "blockdevices": [{
            "path": "/dev/sdz",
            "type": "disk",
            "children": [{"path": "/dev/sdz1", "type": "part", "start": 4096}],
        }]
    }
    assert str(find_partition_path(data, 4096)) == "/dev/sdz1"


def test_inventory_tree_collects_metadata_without_contents(tmp_path):
    folder = tmp_path / "Dokumente"
    folder.mkdir()
    sample = folder / "Bericht.PDF"
    sample.write_bytes(b"1234")
    files, directories = inventory_tree(tmp_path, "004")
    assert [item["path"] for item in directories] == ["Dokumente"]
    assert files[0]["path"] == "Dokumente/Bericht.PDF"
    assert files[0]["size"] == 4
    assert files[0]["original_extension"] == "PDF"
    assert files[0]["category"] == "Dokumente"


def test_inventory_tree_includes_hidden_files_and_directories(tmp_path):
    hidden_folder = tmp_path / ".intern"
    hidden_folder.mkdir()
    (tmp_path / ".hinweis.txt").write_text("sichtbar im Inventar", encoding="utf-8")
    (hidden_folder / ".daten.csv").write_text("a,b\n", encoding="utf-8")

    files, directories = inventory_tree(tmp_path, "001")

    assert [item["path"] for item in directories] == [".intern"]
    assert {item["path"] for item in files} == {".hinweis.txt", ".intern/.daten.csv"}

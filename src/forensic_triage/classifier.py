"""Extension-based file classification for metadata-only triage."""

from __future__ import annotations

from pathlib import PurePosixPath


CATEGORY_EXTENSIONS: dict[str, set[str]] = {
    "Bilder": {"jpg", "jpeg", "png", "gif", "heic", "tif", "tiff", "bmp", "webp", "raw"},
    "Audio": {"mp3", "flac", "wav", "aac", "m4a", "ogg", "wma"},
    "Video": {"mp4", "mov", "avi", "mkv", "wmv", "mpeg", "mpg", "webm"},
    "Dokumente": {"pdf", "doc", "docx", "odt", "rtf"},
    "Tabellen": {"xls", "xlsx", "xlsm", "ods", "csv", "tsv"},
    "Präsentationen": {"ppt", "pptx", "odp", "key"},
    "E-Mail": {"eml", "msg", "pst", "ost", "mbox"},
    "Datenbanken": {"db", "sqlite", "sqlite3", "mdb", "accdb", "sql"},
    "Archive": {"zip", "rar", "7z", "tar", "gz", "bz2", "xz", "tgz"},
    "Programme": {"exe", "dll", "msi", "app", "apk", "deb", "rpm", "sh", "bat", "ps1"},
    "Datenträger-/Backup-Images": {"iso", "img", "dmg", "vhd", "vhdx", "vmdk", "qcow", "qcow2", "bak"},
    "Text/Logs": {"txt", "log", "md", "ini", "cfg", "conf"},
    "Web-Dateien": {"html", "htm", "css", "js", "json", "xml", "yaml", "yml"},
}

EXTENSION_CATEGORY = {
    extension: category
    for category, extensions in CATEGORY_EXTENSIONS.items()
    for extension in extensions
}


def extension_for(path: str) -> str:
    """Return the normalized extension without a leading dot."""
    suffix = PurePosixPath(path).suffix
    return suffix[1:].casefold() if suffix and suffix != "." else ""


def original_extension_for(path: str) -> str:
    """Return the extension exactly as present in the filename."""
    suffix = PurePosixPath(path).suffix
    return suffix[1:] if suffix and suffix != "." else ""


def classify(path: str) -> tuple[str, str]:
    """Return normalized extension and objective extension category."""
    extension = extension_for(path)
    if not extension:
        return extension, "Unbekannt"
    return extension, EXTENSION_CATEGORY.get(extension, "Unbekannt")

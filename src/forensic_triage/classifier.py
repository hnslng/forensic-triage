"""Extension-based file classification for metadata-only triage."""

from __future__ import annotations

from pathlib import PurePosixPath


CATEGORY_EXTENSIONS: dict[str, set[str]] = {
    "Bilder": {"jpg", "jpeg", "png", "gif", "heic", "heif", "avif", "tif", "tiff", "bmp", "webp", "dng", "cr2", "cr3", "nef", "nrw", "arw", "orf", "rw2", "raf", "pef", "psd", "svg", "ico"},
    "Audio": {"mp3", "flac", "wav", "aac", "m4a", "ogg", "wma", "opus", "aif", "aiff", "m4b", "amr", "mid", "midi"},
    "Video": {"mp4", "mov", "avi", "mkv", "wmv", "mpeg", "mpg", "webm", "m4v", "mts", "m2ts", "3gp", "3g2", "vob", "flv", "mxf"},
    "Dokumente": {"pdf", "doc", "docx", "docm", "dot", "dotx", "dotm", "odt", "ott", "rtf", "pages", "epub"},
    "Tabellen": {"xls", "xlsx", "xlsm", "xlsb", "xlt", "xltx", "xltm", "ods", "ots", "csv", "tsv", "numbers"},
    "Präsentationen": {"ppt", "pptx", "pptm", "pps", "ppsx", "ppsm", "pot", "potx", "potm", "odp", "otp"},
    "E-Mail": {"eml", "emlx", "msg", "pst", "ost", "mbox", "mbx"},
    "Datenbanken": {"db", "sqlite", "sqlite3", "mdb", "accdb", "sql"},
    "Archive": {"zip", "rar", "7z", "tar", "gz", "bz2", "xz", "tgz", "tbz2", "txz", "cab", "zipx", "zst", "lz4", "lz", "lzma", "ace", "arj"},
    "Programme": {"exe", "dll", "msi", "app", "apk", "deb", "rpm", "sh", "bat", "ps1", "cmd", "com", "scr", "jar", "py", "vbs", "psm1"},
    "Datenträger-/Backup-Images": {"iso", "img", "dmg", "vhd", "vhdx", "vmdk", "qcow", "qcow2", "e01", "ex01", "aff", "aff4", "ad1", "dd", "wim", "esd", "vdi"},
    "Sicherungskopien": {"bak", "backup", "bkp"},
    "Schutz-/Schlüsseldateien": {"gpg", "pgp", "age", "kdbx", "kdb", "p12", "pfx", "pem", "crt", "cer"},
    "Systemartefakte": {"evtx", "evt", "reg", "lnk", "hiv", "pf"},
    "Kontakte/Kalender": {"vcf", "ics", "vcs"},
    "Mehrdeutig": {"raw", "key"},
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

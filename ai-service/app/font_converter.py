"""
Vietnamese Legacy Font Converter (TCVN3 / ABC -> Unicode).
Converts text extracted from legacy Vietnamese documents to standard UTF-8 Unicode.
"""

# TCVN3 char mapping (when TCVN3 bytes are read as latin1/windows-1252)
TCVN3_TO_UNICODE = {
    "\xa1": "Ă", "\xa2": "Â", "\xa3": "Ê", "\xa4": "Ô", "\xa5": "Ơ", "\xa6": "Ư", "\xa7": "Đ",
    "\xb5": "à", "\xb8": "á", "\xb6": "ả", "\xb7": "ã", "\xb9": "ạ",
    "\xbb": "ằ", "\xbe": "ắ", "\xbc": "ẳ", "\xbd": "ẵ", "\xc0": "ặ", "\xba": "ă",
    "\xc2": "ầ", "\xc5": "ấ", "\xc3": "ẩ", "\xc4": "ẫ", "\xc7": "ậ", "\xc1": "â",
    "\xc9": "è", "\xca": "é", "\xcb": "ẻ", "\xcc": "ẽ", "\xce": "ẹ",
    "\xcf": "ề", "\xd2": "ế", "\xd0": "ể", "\xd1": "ễ", "\xd4": "ệ", "\xcd": "ê",
    "\xd5": "ì", "\xd6": "í", "\xd7": "ỉ", "\xd8": "ĩ", "\xdc": "ị",
    "\xde": "ò", "\xdf": "ó", "\xe1": "ỏ", "\xe2": "õ", "\xe3": "ọ",
    "\xe5": "ồ", "\xe8": "ố", "\xe6": "ổ", "\xe7": "ỗ", "\xea": "ộ", "\xe4": "ô",
    "\xec": "ờ", "\xed": "ớ", "\xee": "ở", "\xef": "ỡ", "\xf1": "ợ", "\xeb": "ơ",
    "\xf2": "ù", "\xf3": "ú", "\xf4": "ủ", "\xf5": "ũ", "\xf7": "ụ",
    "\xf8": "ư", "\xf9": "ừ", "\xfa": "ứ", "\xfb": "ử", "\xfc": "ữ", "\xfe": "ự",
    "\xfd": "ý", "\xff": "ỹ",
}

# Distinctive TCVN3 markers that do NOT overlap with normal Unicode text
TCVN3_MARKERS = set(TCVN3_TO_UNICODE.keys())


def is_tcvn3_encoded(text: str) -> bool:
    """
    Check if a text string is encoded in TCVN3 rather than UTF-8.
    """
    if not text:
        return False

    # Count occurrences of TCVN3 specific latin1 characters
    marker_count = sum(1 for char in text if char in TCVN3_MARKERS)
    # Check if string contains standard Vietnamese Unicode characters (e.g. U+1EA0..U+1EF9)
    unicode_vietnamese_count = sum(1 for char in text if 0x1EA0 <= ord(char) <= 0x1EF9)

    # If there are many TCVN3 markers and very few native Unicode Vietnamese characters
    return marker_count > 3 and unicode_vietnamese_count == 0


def normalize_vietnamese_text(text: str) -> str:
    """
    Detect and normalize Vietnamese text encodings to standard Unicode.
    """
    if not text:
        return ""

    if is_tcvn3_encoded(text):
        converted = [TCVN3_TO_UNICODE.get(char, char) for char in text]
        return "".join(converted)

    return text

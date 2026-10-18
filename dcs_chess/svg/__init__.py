"""SVG board and piece rendering."""

from __future__ import annotations

import math
import re
from typing import Dict, Iterable, Optional, Tuple, Union

from dcs_chess.core.constants import (
    WHITE, BLACK,
    SQUARE_NAMES,
    FILE_NAMES,
)
from dcs_chess.core.piece import Piece

Square = int
Color = bool
IntoSquareSet = Union[int, Iterable[int]]

__all__ = [
    "Arrow", "COORDS", "CHECK_GRADIENT", "DEFAULT_COLORS",
    "MARGIN", "PIECES", "SQUARE_SIZE", "XX",
    "board", "piece",
]

SQUARE_SIZE = 45
MARGIN = 20

DEFAULT_COLORS: Dict[str, str] = {
    "square light": "#ffce9e",
    "square dark": "#d18b47",
    "square dark lastmove": "#aaa23b",
    "square light lastmove": "#cdd16a",
    "margin": "#212121",
    "inner border": "#111",
    "outer border": "#111",
    "coord": "#e5e5e5",
    "arrow green": "#15781B80",
    "arrow red": "#88202080",
    "arrow yellow": "#e68f00b3",
    "arrow blue": "#00308880",
}

CHECK_GRADIENT = '<radialGradient id="check_gradient" r="0.5"><stop offset="0%" stop-color="#ff0000" stop-opacity="1.0" /><stop offset="50%" stop-color="#e70000" stop-opacity="1.0" /><stop offset="100%" stop-color="#9e0000" stop-opacity="0.0" /></radialGradient>'

XX = '<g id="xx"><path d="M35.865 9.135a1.89 1.89 0 0 1 0 2.673L25.173 22.5l10.692 10.692a1.89 1.89 0 0 1 0 2.673 1.89 1.89 0 0 1-2.673 0L22.5 25.173 11.808 35.865a1.89 1.89 0 0 1-2.673 0 1.89 1.89 0 0 1 0-2.673L19.827 22.5 9.135 11.808a1.89 1.89 0 0 1 0-2.673 1.89 1.89 0 0 1 2.673 0L22.5 19.827 33.192 9.135a1.89 1.89 0 0 1 2.673 0z" fill="#000" stroke="#fff" stroke-width="1.688"/></g>'

PIECES: Dict[str, str] = {
    "B": '<g id="white-bishop" class="white bishop" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><g fill="#fff" stroke-linecap="butt"><path d="M9 36c3.39-.97 10.11.43 13.5-2 3.39 2.43 10.11 1.03 13.5 2 0 0 1.65.54 3 2-.68.97-1.65.99-3 .5-3.39-.97-10.11.46-13.5-1-3.39 1.46-10.11.03-13.5 1-1.354.49-2.323.47-3-.5 1.354-1.94 3-2 3-2zM15 32c2.5 2.5 12.5 2.5 15 0 .5-1.5 0-2 0-2 0-2.5-2.5-4-2.5-4 5.5-1.5 6-11.5-5-15.5-11 4-10.5 14-5 15.5 0 0-2.5 1.5-2.5 4 0 0-.5.5 0 2zM25 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 1 1 5 0z"/></g><path d="M17.5 26h10M15 30h15m-7.5-14.5v5M20 18h5" stroke-linejoin="miter"/></g>',
    "K": '<g id="white-king" class="white king" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22.5 11.63V6M20 8h5" stroke-linejoin="miter"/><path d="M22.5 25s4.5-7.5 3-10.5c0 0-1-2.5-3-2.5s-3 2.5-3 2.5c-1.5 3 3 10.5 3 10.5" fill="#fff" stroke-linecap="butt" stroke-linejoin="miter"/><path d="M11.5 37c5.5 3.5 15.5 3.5 21 0v-7s9-4.5 6-10.5c-4-6.5-13.5-3.5-16 4V27v-3.5c-3.5-7.5-13-10.5-16-4-3 6 5 10 5 10V37z" fill="#fff"/><path d="M11.5 30c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0"/></g>',
    "N": '<g id="white-knight" class="white knight" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M 22,10 C 32.5,11 38.5,18 38,39 L 15,39 C 15,30 25,32.5 23,18" style="fill:#ffffff; stroke:#000000;"/><path d="M 24,18 C 24.38,20.91 18.45,25.37 16,27 C 13,29 13.18,31.34 11,31 C 9.958,30.06 12.41,27.96 11,28 C 10,28 11.19,29.23 10,30 C 9,30 5.997,31 6,26 C 6,24 12,14 12,14 C 12,14 13.89,12.1 14,10.5 C 13.27,9.506 13.5,8.5 13.5,7.5 C 14.5,6.5 16.5,10 16.5,10 L 18.5,10 C 18.5,10 19.28,8.008 21,7 C 22,7 22,10 22,10" style="fill:#ffffff; stroke:#000000;"/><path d="M 9.5 25.5 A 0.5 0.5 0 1 1 8.5,25.5 A 0.5 0.5 0 1 1 9.5 25.5 z" style="fill:#000000; stroke:#000000;"/><path d="M 15 15.5 A 0.5 1.5 0 1 1 14,15.5 A 0.5 1.5 0 1 1 15 15.5 z" transform="matrix(0.866,0.5,-0.5,0.866,9.693,-5.173)" style="fill:#000000; stroke:#000000;"/></g>',
    "P": '<g id="white-pawn" class="white pawn"><path d="M22.5 9c-2.21 0-4 1.79-4 4 0 .89.29 1.71.78 2.38C17.33 16.5 16 18.59 16 21c0 2.03.94 3.84 2.41 5.03-3 1.06-7.41 5.55-7.41 13.47h23c0-7.92-4.41-12.41-7.41-13.47 1.47-1.19 2.41-3 2.41-5.03 0-2.41-1.33-4.5-3.28-5.62.49-.67.78-1.49.78-2.38 0-2.21-1.79-4-4-4z" fill="#fff" stroke="#000" stroke-width="1.5" stroke-linecap="round"/></g>',
    "Q": '<g id="white-queen" class="white queen" fill="#fff" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 12a2 2 0 1 1-4 0 2 2 0 1 1 4 0zM24.5 7.5a2 2 0 1 1-4 0 2 2 0 1 1 4 0zM41 12a2 2 0 1 1-4 0 2 2 0 1 1 4 0zM16 8.5a2 2 0 1 1-4 0 2 2 0 1 1 4 0zM33 9a2 2 0 1 1-4 0 2 2 0 1 1 4 0z"/><path d="M9 26c8.5-1.5 21-1.5 27 0l2-12-7 11V11l-5.5 13.5-3-15-3 15-5.5-14V25L7 14l2 12zM9 26c0 2 1.5 2 2.5 4 1 1.5 1 1 .5 3.5-1.5 1-1.5 2.5-1.5 2.5-1.5 1.5.5 2.5.5 2.5 6.5 1 16.5 1 23 0 0 0 1.5-1 0-2.5 0 0 .5-1.5-1-2.5-.5-2.5-.5-2 .5-3.5 1-2 2.5-2 2.5-4-8.5-1.5-18.5-1.5-27 0z" stroke-linecap="butt"/><path d="M11.5 30c3.5-1 18.5-1 22 0M12 33.5c6-1 15-1 21 0" fill="none"/></g>',
    "R": '<g id="white-rook" class="white rook" fill="#fff" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 39h27v-3H9v3zM12 36v-4h21v4H12zM11 14V9h4v2h5V9h5v2h5V9h4v5" stroke-linecap="butt"/><path d="M34 14l-3 3H14l-3-3"/><path d="M31 17v12.5H14V17" stroke-linecap="butt" stroke-linejoin="miter"/><path d="M31 29.5l1.5 2.5h-20l1.5-2.5"/><path d="M11 14h23" fill="none" stroke-linejoin="miter"/></g>',
    "b": '<g id="black-bishop" class="black bishop" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 36c3.39-.97 10.11.43 13.5-2 3.39 2.43 10.11 1.03 13.5 2 0 0 1.65.54 3 2-.68.97-1.65.99-3 .5-3.39-.97-10.11.46-13.5-1-3.39 1.46-10.11.03-13.5 1-1.354.49-2.323.47-3-.5 1.354-1.94 3-2 3-2zm6-4c2.5 2.5 12.5 2.5 15 0 .5-1.5 0-2 0-2 0-2.5-2.5-4-2.5-4 5.5-1.5 6-11.5-5-15.5-11 4-10.5 14-5 15.5 0 0-2.5 1.5-2.5 4 0 0-.5.5 0 2zM25 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 1 1 5 0z" fill="#000" stroke-linecap="butt"/><path d="M17.5 26h10M15 30h15m-7.5-14.5v5M20 18h5" stroke="#fff" stroke-linejoin="miter"/></g>',
    "k": '<g id="black-king" class="black king" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22.5 11.63V6" stroke-linejoin="miter"/><path d="M22.5 25s4.5-7.5 3-10.5c0 0-1-2.5-3-2.5s-3 2.5-3 2.5c-1.5 3 3 10.5 3 10.5" fill="#000" stroke-linecap="butt" stroke-linejoin="miter"/><path d="M11.5 37c5.5 3.5 15.5 3.5 21 0v-7s9-4.5 6-10.5c-4-6.5-13.5-3.5-16 4V27v-3.5c-3.5-7.5-13-10.5-16-4-3 6 5 10 5 10V37z" fill="#000"/><path d="M20 8h5" stroke-linejoin="miter"/><path d="M32 29.5s8.5-4 6.03-9.65C34.15 14 25 18 22.5 24.5l.01 2.1-.01-2.1C20 18 9.906 14 6.997 19.85c-2.497 5.65 4.853 9 4.853 9M11.5 30c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0" stroke="#fff"/></g>',
    "n": '<g id="black-knight" class="black knight" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M 22,10 C 32.5,11 38.5,18 38,39 L 15,39 C 15,30 25,32.5 23,18" style="fill:#000000; stroke:#000000;"/><path d="M 24,18 C 24.38,20.91 18.45,25.37 16,27 C 13,29 13.18,31.34 11,31 C 9.958,30.06 12.41,27.96 11,28 C 10,28 11.19,29.23 10,30 C 9,30 5.997,31 6,26 C 6,24 12,14 12,14 C 12,14 13.89,12.1 14,10.5 C 13.27,9.506 13.5,8.5 13.5,7.5 C 14.5,6.5 16.5,10 16.5,10 L 18.5,10 C 18.5,10 19.28,8.008 21,7 C 22,7 22,10 22,10" style="fill:#000000; stroke:#000000;"/><path d="M 9.5 25.5 A 0.5 0.5 0 1 1 8.5,25.5 A 0.5 0.5 0 1 1 9.5 25.5 z" style="fill:#ececec; stroke:#ececec;"/><path d="M 15 15.5 A 0.5 1.5 0 1 1 14,15.5 A 0.5 1.5 0 1 1 15 15.5 z" transform="matrix(0.866,0.5,-0.5,0.866,9.693,-5.173)" style="fill:#ececec; stroke:#ececec;"/><path d="M 24.55,10.4 L 24.1,11.85 L 24.6,12 C 27.75,13 30.25,14.49 32.5,18.75 C 34.75,23.01 35.75,29.06 35.25,39 L 35.2,39.5 L 37.45,39.5 L 37.5,39 C 38,28.94 36.62,22.15 34.25,17.66 C 31.88,13.17 28.46,11.02 25.06,10.5 L 24.55,10.4 z " style="fill:#ececec; stroke:none;"/></g>',
    "p": '<g id="black-pawn" class="black pawn"><path d="M22.5 9c-2.21 0-4 1.79-4 4 0 .89.29 1.71.78 2.38C17.33 16.5 16 18.59 16 21c0 2.03.94 3.84 2.41 5.03-3 1.06-7.41 5.55-7.41 13.47h23c0-7.92-4.41-12.41-7.41-13.47 1.47-1.19 2.41-3 2.41-5.03 0-2.41-1.33-4.5-3.28-5.62.49-.67.78-1.49.78-2.38 0-2.21-1.79-4-4-4z" fill="#000" stroke="#000" stroke-width="1.5" stroke-linecap="round"/></g>',
    "q": '<g id="black-queen" class="black queen" fill="#000" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><g fill="#000" stroke="none"><circle cx="6" cy="12" r="2.75"/><circle cx="14" cy="9" r="2.75"/><circle cx="22.5" cy="8" r="2.75"/><circle cx="31" cy="9" r="2.75"/><circle cx="39" cy="12" r="2.75"/></g><path d="M9 26c8.5-1.5 21-1.5 27 0l2.5-12.5L31 25l-.3-14.1-5.2 13.6-3-14.5-3 14.5-5.2-13.6L14 25 6.5 13.5 9 26zM9 26c0 2 1.5 2 2.5 4 1 1.5 1 1 .5 3.5-1.5 1-1.5 2.5-1.5 2.5-1.5 1.5.5 2.5.5 2.5 6.5 1 16.5 1 23 0 0 0 1.5-1 0-2.5 0 0 .5-1.5-1-2.5-.5-2.5-.5-2 .5-3.5 1-2 2.5-2 2.5-4-8.5-1.5-18.5-1.5-27 0z" stroke-linecap="butt"/><path d="M11 38.5a35 35 1 0 0 23 0" fill="none" stroke-linecap="butt"/><path d="M11 29a35 35 1 0 1 23 0M12.5 31.5h20M11.5 34.5a35 35 1 0 0 22 0M10.5 37.5a35 35 1 0 0 24 0" fill="none" stroke="#fff"/></g>',
    "r": '<g id="black-rook" class="black rook" fill="#000" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 39h27v-3H9v3zM12.5 32l1.5-2.5h17l1.5 2.5h-20zM12 36v-4h21v4H12z" stroke-linecap="butt"/><path d="M14 29.5v-13h17v13H14z" stroke-linecap="butt" stroke-linejoin="miter"/><path d="M14 16.5L11 14h23l-3 2.5H14zM11 14V9h4v2h5V9h5v2h5V9h4v5H11z" stroke-linecap="butt"/><path d="M12 35.5h21M13 31.5h19M14 29.5h17M14 16.5h17M11 14h23" fill="none" stroke="#fff" stroke-width="1" stroke-linejoin="miter"/></g>',
}

COORDS: Dict[str, str] = {
    "1": '<path d="M6.754 26.996h2.578v-8.898l-2.805.562v-1.437l2.79-.563h1.578v10.336h2.578v1.328h-6.72z"/>',
    "2": '<path d="M8.195 26.996h5.508v1.328H6.297v-1.328q.898-.93 2.445-2.492 1.555-1.57 1.953-2.024.758-.851 1.055-1.437.305-.594.305-1.164 0-.93-.657-1.516-.648-.586-1.695-.586-.742 0-1.57.258-.82.258-1.758.781v-1.593q.953-.383 1.781-.578.828-.196 1.516-.196 1.812 0 2.89.906 1.079.907 1.079 2.422 0 .72-.274 1.368-.265.64-.976 1.515-.196.227-1.243 1.313-1.046 1.078-2.953 3.023z"/>',
    "3": '<path d="M11.434 22.035q1.132.242 1.765 1.008.64.766.64 1.89 0 1.727-1.187 2.672-1.187.946-3.375.946-.734 0-1.515-.149-.774-.14-1.602-.43V26.45q.656.383 1.438.578.78.196 1.632.196 1.485 0 2.258-.586.782-.586.782-1.703 0-1.032-.727-1.61-.719-.586-2.008-.586h-1.36v-1.297h1.423q1.164 0 1.78-.46.618-.47.618-1.344 0-.899-.64-1.375-.633-.485-1.82-.485-.65 0-1.391.141-.743.14-1.633.437V16.95q.898-.25 1.68-.375.788-.125 1.484-.125 1.797 0 2.844.82 1.046.813 1.046 2.204 0 .968-.554 1.64-.555.664-1.578.922z"/>',
    "4": '<path d="M11.016 18.035L7.03 24.262h3.985zm-.414-1.375h1.984v7.602h1.664v1.312h-1.664v2.75h-1.57v-2.75H5.75v-1.523z"/>',
    "5": '<path d="M6.719 16.66h6.195v1.328h-4.75v2.86q.344-.118.688-.172.343-.063.687-.063 1.953 0 3.094 1.07 1.14 1.07 1.14 2.899 0 1.883-1.171 2.93-1.172 1.039-3.305 1.039-.735 0-1.5-.125-.758-.125-1.57-.375v-1.586q.703.383 1.453.57.75.188 1.586.188 1.351 0 2.14-.711.79-.711.79-1.93 0-1.219-.79-1.93-.789-.71-2.14-.71-.633 0-1.266.14-.625.14-1.281.438z"/>',
    "6": '<path d="M10.137 21.863q-1.063 0-1.688.727-.617.726-.617 1.992 0 1.258.617 1.992.625.727 1.688.727 1.062 0 1.68-.727.624-.734.624-1.992 0-1.266-.625-1.992-.617-.727-1.68-.727zm3.133-4.945v1.437q-.594-.28-1.204-.43-.601-.148-1.195-.148-1.562 0-2.39 1.055-.82 1.055-.938 3.188.46-.68 1.156-1.04.696-.367 1.531-.367 1.758 0 2.774 1.07 1.023 1.063 1.023 2.899 0 1.797-1.062 2.883-1.063 1.086-2.828 1.086-2.024 0-3.094-1.547-1.07-1.555-1.07-4.5 0-2.766 1.312-4.406 1.313-1.649 3.524-1.649.593 0 1.195.117.61.118 1.266.352z"/>',
    "7": '<path d="M6.25 16.66h7.5v.672L9.516 28.324H7.867l3.985-10.336H6.25z"/>',
    "8": '<path d="M10 22.785q-1.125 0-1.773.602-.641.601-.641 1.656t.64 1.656q.649.602 1.774.602t1.773-.602q.649-.61.649-1.656 0-1.055-.649-1.656-.64-.602-1.773-.602zm-1.578-.672q-1.016-.25-1.586-.945-.563-.695-.563-1.695 0-1.399.993-2.211 1-.813 2.734-.813 1.742 0 2.734.813.993.812.993 2.21 0 1-.57 1.696-.563.695-1.571.945 1.14.266 1.773 1.04.641.773.641 1.89 0 1.695-1.04 2.602-1.03.906-2.96.906t-2.969-.906Q6 26.738 6 25.043q0-1.117.64-1.89.641-.774 1.782-1.04zm-.578-2.492q0 .906.562 1.414.57.508 1.594.508 1.016 0 1.586-.508.578-.508.578-1.414 0-.906-.578-1.414-.57-.508-1.586-.508-1.023 0-1.594.508-.562.508-.562 1.414z"/>',
    "a": '<path d="M23.328 10.016q-1.742 0-2.414.398-.672.398-.672 1.36 0 .765.5 1.218.508.445 1.375.445 1.196 0 1.914-.843.727-.852.727-2.258v-.32zm2.867-.594v4.992h-1.437v-1.328q-.492.797-1.227 1.18-.734.375-1.797.375-1.343 0-2.14-.75-.79-.758-.79-2.024 0-1.476.985-2.226.992-.75 2.953-.75h2.016V8.75q0-.992-.656-1.531-.649-.547-1.829-.547-.75 0-1.46.18-.711.18-1.368.539V6.062q.79-.304 1.532-.453.742-.156 1.445-.156 1.898 0 2.836.984.937.985.937 2.985z"/>',
    "b": '<path d="M24.922 10.047q0-1.586-.656-2.485-.649-.906-1.79-.906-1.14 0-1.796.906-.649.899-.649 2.485 0 1.586.649 2.492.656.898 1.797.898 1.14 0 1.789-.898.656-.906.656-2.492zm-4.89-3.055q.452-.781 1.14-1.156.695-.383 1.656-.383 1.594 0 2.586 1.266 1 1.265 1 3.328 0 2.062-1 3.328-.992 1.266-2.586 1.266-.96 0-1.656-.375-.688-.383-1.14-1.164v1.312h-1.446V2.258h1.445z"/>',
    "c": '<path d="M25.96 6v1.344q-.608-.336-1.226-.5-.609-.172-1.234-.172-1.398 0-2.172.89-.773.883-.773 2.485 0 1.601.773 2.492.774.883 2.172.883.625 0 1.234-.164.618-.172 1.227-.508v1.328q-.602.281-1.25.422-.64.14-1.367.14-1.977 0-3.14-1.242-1.165-1.242-1.165-3.351 0-2.14 1.172-3.367 1.18-1.227 3.227-1.227.664 0 1.296.14.633.134 1.227.407z"/>',
    "d": '<path d="M24.973 6.992V2.258h1.437v12.156h-1.437v-1.312q-.453.78-1.149 1.164-.687.375-1.656.375-1.586 0-2.586-1.266-.992-1.266-.992-3.328 0-2.063.992-3.328 1-1.266 2.586-1.266.969 0 1.656.383.696.375 1.149 1.156zm-4.899 3.055q0 1.586.649 2.492.656.898 1.797.898 1.14 0 1.796-.898.657-.906.657-2.492 0-1.586-.657-2.485-.656-.906-1.796-.906-1.141 0-1.797.906-.649.899-.649 2.485z"/>',
    "e": '<path d="M26.555 9.68v.703h-6.61q.094 1.484.89 2.265.806.774 2.235.774.828 0 1.602-.203.781-.203 1.547-.61v1.36q-.774.328-1.586.5-.813.172-1.649.172-2.093 0-3.32-1.22-1.219-1.218-1.219-3.296 0-2.148 1.157-3.406 1.164-1.266 3.132-1.266 1.766 0 2.79 1.14 1.03 1.134 1.03 3.087zm-1.438-.422q-.015-1.18-.664-1.883-.64-.703-1.703-.703-1.203 0-1.93.68-.718.68-.828 1.914z"/>',
    "f": '<path d="M25.285 2.258v1.195H23.91q-.773 0-1.078.313-.297.312-.297 1.125v.773h2.367v1.117h-2.367v7.633H21.09V6.781h-1.375V5.664h1.375v-.61q0-1.46.68-2.124.68-.672 2.156-.672z"/>',
    "g": '<path d="M24.973 9.937q0-1.562-.649-2.421-.64-.86-1.804-.86-1.157 0-1.805.86-.64.859-.64 2.421 0 1.555.64 2.415.648.859 1.805.859 1.164 0 1.804-.86.649-.859.649-2.414zm1.437 3.391q0 2.234-.992 3.32-.992 1.094-3.04 1.094-.757 0-1.429-.117-.672-.11-1.304-.344v-1.398q.632.344 1.25.508.617.164 1.257.164 1.414 0 2.118-.743.703-.734.703-2.226v-.711q-.446.773-1.141 1.156-.695.383-1.664.383-1.61 0-2.594-1.227-.984-1.226-.984-3.25 0-2.03.984-3.257.985-1.227 2.594-1.227.969 0 1.664.383t1.14 1.156V5.664h1.438z"/>',
    "h": '<path d="M26.164 9.133v5.281h-1.437V9.18q0-1.243-.485-1.86-.484-.617-1.453-.617-1.164 0-1.836.742-.672.742-.672 2.024v4.945h-1.445V2.258h1.445v4.765q.516-.789 1.211-1.18.703-.39 1.617-.39 1.508 0 2.282.938.773.93.773 2.742z"/>',
}

_PIECE_IDS = {
    "P": "white-pawn", "N": "white-knight", "B": "white-bishop",
    "R": "white-rook", "Q": "white-queen", "K": "white-king",
    "p": "black-pawn", "n": "black-knight", "b": "black-bishop",
    "r": "black-rook", "q": "black-queen", "k": "black-king",
}


class SvgWrapper(str):
    def _repr_svg_(self) -> str:
        return str(self)


class Arrow:
    def __init__(self, tail: Square, head: Square, *, color: str = "green") -> None:
        self.tail = tail
        self.head = head
        self.color = color

    @classmethod
    def from_pgn(cls, pgn: str) -> Arrow:
        color_map = {"G": "green", "R": "red", "Y": "yellow", "B": "blue"}
        if pgn[0] in color_map:
            color = color_map[pgn[0]]
            rest = pgn[1:]
        else:
            color = "green"
            rest = pgn
        if len(rest) == 2:
            sq = SQUARE_NAMES.index(rest)
            return cls(sq, sq, color=color)
        tail = SQUARE_NAMES.index(rest[:2])
        head = SQUARE_NAMES.index(rest[2:4])
        return cls(tail, head, color=color)

    def pgn(self) -> str:
        color_map = {"green": "G", "red": "R", "yellow": "Y", "blue": "B"}
        prefix = color_map.get(self.color, "G")
        tail_name = SQUARE_NAMES[self.tail]
        head_name = SQUARE_NAMES[self.head]
        if self.tail == self.head:
            return prefix + tail_name
        return prefix + tail_name + head_name

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Arrow):
            return self.tail == other.tail and self.head == other.head and self.color == other.color
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.tail, self.head, self.color))

    def __repr__(self) -> str:
        return f"Arrow({SQUARE_NAMES[self.tail]!r}, {SQUARE_NAMES[self.head]!r}, color={self.color!r})"


def _sq_file(sq: int) -> int:
    return sq & 7


def _sq_rank(sq: int) -> int:
    return sq >> 3


def _color_str(key: str, colors: Dict[str, str]) -> str:
    return colors.get(key, DEFAULT_COLORS.get(key, ""))


_RE_CLOSE = re.compile(r'(?<! )/>')


def _xml_close(s: str) -> str:
    return _RE_CLOSE.sub(' />', s)


def _parse_color(raw: str) -> tuple[str, float]:
    if len(raw) == 9 and raw.startswith("#"):
        return raw[:7], int(raw[7:9], 16) / 255.0
    return raw, 1.0


def _sq_xy(sq: int, effective_white: bool, board_start: int) -> tuple[int, int]:
    f, r = _sq_file(sq), _sq_rank(sq)
    if effective_white:
        return board_start + f * SQUARE_SIZE, board_start + (7 - r) * SQUARE_SIZE
    return board_start + (7 - f) * SQUARE_SIZE, board_start + r * SQUARE_SIZE


def piece(piece: Piece, size: Optional[int] = None) -> str:
    svg_data = PIECES.get(piece.symbol(), "")
    if not svg_data:
        return SvgWrapper("")

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {SQUARE_SIZE} {SQUARE_SIZE}"']
    if size is not None:
        parts.append(f' width="{size}" height="{size}"')
    parts.append(">")
    parts.append(_xml_close(svg_data))
    parts.append("</svg>")
    return SvgWrapper("".join(parts))


def board(
    board: Optional[object] = None,
    *,
    orientation: Color = WHITE,
    lastmove: Optional[object] = None,
    check: Optional[Square] = None,
    arrows: Iterable[Union[Arrow, tuple[Square, Square]]] = [],
    fill: Dict[Square, str] = {},
    squares: Optional[IntoSquareSet] = None,
    size: Optional[int] = None,
    coordinates: bool = True,
    colors: Dict[str, str] = {},
    flipped: bool = False,
    borders: bool = False,
    style: Optional[str] = None,
) -> str:
    is_white = orientation if not flipped else not orientation

    margin = 15 if coordinates else 0
    outer_border = 1 if borders else 0
    inner_border = 1 if (borders and coordinates) else 0
    board_start = outer_border + margin + inner_border
    board_px = 8 * SQUARE_SIZE
    vb = board_px + 2 * board_start

    parts: list[str] = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {vb} {vb}"')
    if size is not None:
        parts.append(f' width="{size}" height="{size}"')
    parts.append(">")

    if style:
        parts.append(f"<style>{style}</style>")

    # Desc
    if board is not None:
        parts.append(f"<desc><pre>{board}</pre></desc>")

    # Defs — piece definitions (only used types), check gradient, xx
    _PIECE_ORDER = "PNBRQKpnbrqk"
    used_symbols: list[str] = []
    if board is not None and hasattr(board, "piece_at"):
        seen: set[str] = set()
        for sq in range(64):
            p = board.piece_at(sq)
            if p is not None:
                seen.add(p.symbol())
        used_symbols = [s for s in _PIECE_ORDER if s in seen]

    sq_set: set[int] = set()
    if squares is not None:
        if isinstance(squares, int):
            bb = squares
            while bb:
                sq_set.add((bb & -bb).bit_length() - 1)
                bb &= bb - 1
        else:
            sq_set = set(squares)

    has_defs = used_symbols or check is not None or sq_set
    if has_defs:
        parts.append("<defs>")
        for sym in used_symbols:
            parts.append(_xml_close(PIECES[sym]))
        if sq_set:
            parts.append(_xml_close(XX))
        if check is not None:
            parts.append(_xml_close(CHECK_GRADIENT))
        parts.append("</defs>")
    else:
        parts.append("<defs />")

    # Borders
    if borders:
        outer_color = _color_str("outer border", colors)
        parts.append(
            f'<rect x="0.5" y="0.5" width="{vb - 1}" height="{vb - 1}" '
            f'fill="none" stroke="{outer_color}" stroke-width="1" />'
        )

    # Margin (coordinate background)
    if coordinates:
        margin_color = _color_str("margin", colors)
        mx = outer_border + margin / 2
        mw = board_px + margin + 2 * inner_border
        parts.append(
            f'<rect x="{mx}" y="{mx}" width="{mw}" height="{mw}" '
            f'fill="none" stroke="{margin_color}" stroke-width="{margin}" />'
        )

    # Inner border
    if borders and coordinates:
        inner_color = _color_str("inner border", colors)
        ix = outer_border + margin + 0.5
        iw = board_px + 1
        parts.append(
            f'<rect x="{ix}" y="{ix}" width="{iw}" height="{iw}" '
            f'fill="none" stroke="{inner_color}" stroke-width="1" />'
        )

    # Coordinates (rendered BEFORE squares, at scale 0.75)
    if coordinates:
        coord_color = _color_str("coord", colors)
        after_board = board_start + board_px + inner_border

        for fi in range(8):
            label = FILE_NAMES[fi]
            coord_svg = _xml_close(COORDS.get(label, ""))
            if not coord_svg:
                continue
            if is_white:
                cx = board_start + fi * SQUARE_SIZE + 5
            else:
                cx = board_start + (7 - fi) * SQUARE_SIZE + 5
            parts.append(
                f'<g transform="translate({cx}, 1) scale(0.75, 0.75)" '
                f'fill="{coord_color}" stroke="{coord_color}">{coord_svg}</g>'
            )
            parts.append(
                f'<g transform="translate({cx}, {after_board}) scale(0.75, 0.75)" '
                f'fill="{coord_color}" stroke="{coord_color}">{coord_svg}</g>'
            )

        for ri in range(8):
            label = str(ri + 1)
            coord_svg = _xml_close(COORDS.get(label, ""))
            if not coord_svg:
                continue
            if is_white:
                cy = board_start + (7 - ri) * SQUARE_SIZE + 5
            else:
                cy = board_start + ri * SQUARE_SIZE + 5
            parts.append(
                f'<g transform="translate(0, {cy}) scale(0.75, 0.75)" '
                f'fill="{coord_color}" stroke="{coord_color}">{coord_svg}</g>'
            )
            parts.append(
                f'<g transform="translate({after_board}, {cy}) scale(0.75, 0.75)" '
                f'fill="{coord_color}" stroke="{coord_color}">{coord_svg}</g>'
            )

    # Squares
    lastmove_sqs: set[int] = set()
    if lastmove is not None and hasattr(lastmove, "from_square") and hasattr(lastmove, "to_square"):
        lastmove_sqs.add(lastmove.from_square)
        lastmove_sqs.add(lastmove.to_square)

    for sq in range(64):
        x, y = _sq_xy(sq, is_white, board_start)
        fi, ri = _sq_file(sq), _sq_rank(sq)
        is_light = (fi + ri) % 2 == 1

        if sq in lastmove_sqs:
            sq_color = _color_str("square light lastmove" if is_light else "square dark lastmove", colors)
        else:
            sq_color = _color_str("square light" if is_light else "square dark", colors)

        cls_ld = "light" if is_light else "dark"
        if sq in lastmove_sqs:
            cls = f"square {cls_ld} lastmove {SQUARE_NAMES[sq]}"
        else:
            cls = f"square {cls_ld} {SQUARE_NAMES[sq]}"
        parts.append(
            f'<rect x="{x}" y="{y}" width="{SQUARE_SIZE}" height="{SQUARE_SIZE}" '
            f'class="{cls}" stroke="none" fill="{sq_color}" />'
        )
        if sq in fill:
            fill_color, fill_opacity = _parse_color(fill[sq])
            if fill_opacity < 1.0:
                parts.append(
                    f'<rect x="{x}" y="{y}" width="{SQUARE_SIZE}" height="{SQUARE_SIZE}" '
                    f'stroke="none" fill="{fill_color}" opacity="{fill_opacity}" />'
                )
            else:
                parts.append(
                    f'<rect x="{x}" y="{y}" width="{SQUARE_SIZE}" height="{SQUARE_SIZE}" '
                    f'stroke="none" fill="{fill_color}" />'
                )

    # Check highlight
    if check is not None:
        cx, cy = _sq_xy(check, is_white, board_start)
        parts.append(
            f'<rect x="{cx}" y="{cy}" width="{SQUARE_SIZE}" height="{SQUARE_SIZE}" '
            f'class="check" fill="url(#check_gradient)" />'
        )

    # Pieces and XX markers (interleaved in square order)
    for sq in range(64):
        if board is not None and hasattr(board, "piece_at"):
            p = board.piece_at(sq)
            if p is not None:
                x, y = _sq_xy(sq, is_white, board_start)
                pid = _PIECE_IDS.get(p.symbol(), "")
                if pid:
                    parts.append(
                        f'<use href="#{pid}" xlink:href="#{pid}" transform="translate({x}, {y})" />'
                    )
        if sq in sq_set:
            x, y = _sq_xy(sq, is_white, board_start)
            parts.append(f'<use href="#xx" xlink:href="#xx" x="{x}" y="{y}" />')

    # Arrows
    for arrow in arrows:
        if isinstance(arrow, tuple):
            arrow = Arrow(arrow[0], arrow[1])

        looked_up = _color_str(f"arrow {arrow.color}", colors)
        if looked_up:
            stroke_color, opacity = _parse_color(looked_up)
        else:
            stroke_color = arrow.color
            opacity = 1.0

        half = SQUARE_SIZE / 2
        tx, ty = _sq_xy(arrow.tail, is_white, board_start)
        hx, hy = _sq_xy(arrow.head, is_white, board_start)
        x1, y1 = tx + half, ty + half
        x2, y2 = hx + half, hy + half

        opacity_attr = f' opacity="{opacity}"' if opacity < 1.0 else ""

        if arrow.tail == arrow.head:
            r = SQUARE_SIZE * 0.45
            sw = SQUARE_SIZE * 0.1
            parts.append(
                f'<circle cx="{x1}" cy="{y1}" r="{r}" '
                f'stroke-width="{sw}" stroke="{stroke_color}"{opacity_attr} '
                f'fill="none" class="circle" />'
            )
        else:
            line_w = SQUARE_SIZE * 0.2
            head_len = SQUARE_SIZE * 0.75
            dx, dy = x2 - x1, y2 - y1
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                ux, uy = dx / dist, dy / dist
                px, py = -uy, ux

                tip_x = x2 - ux * (line_w / 2)
                tip_y = y2 - uy * (line_w / 2)
                base_x = x2 - ux * (head_len + line_w / 2)
                base_y = y2 - uy * (head_len + line_w / 2)

                half_w = head_len / 2
                parts.append(
                    f'<line x1="{x1}" y1="{y1}" x2="{base_x}" y2="{base_y}" '
                    f'stroke="{stroke_color}"{opacity_attr} '
                    f'stroke-width="{line_w}" stroke-linecap="butt" class="arrow" />'
                )
                parts.append(
                    f'<polygon points="{tip_x},{tip_y} '
                    f'{base_x - px * half_w},{base_y - py * half_w} '
                    f'{base_x + px * half_w},{base_y + py * half_w}" '
                    f'fill="{stroke_color}"{opacity_attr} class="arrow" />'
                )

    parts.append("</svg>")
    return SvgWrapper("".join(parts))

from pathlib import Path
import runpy
import unittest
import xml.etree.ElementTree as ET


render = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/style-profile-stats.py"))["render_cards"]
STATS = '''<svg xmlns="http://www.w3.org/2000/svg">
<text data-testid="header">Xuan &amp; Loc's GitHub Stats</text>
<text data-testid="level-rank-icon">C</text>
<text data-testid="stars">4</text><text data-testid="commits">167</text>
<text data-testid="prs">0</text><text data-testid="issues">0</text>
<text data-testid="contribs">3</text></svg>'''
LANGUAGES = '''<svg xmlns="http://www.w3.org/2000/svg">
<rect data-testid="lang-progress" fill="#3178c6"/>
<rect data-testid="lang-progress" fill="#3572a5"/>
<text data-testid="lang-name">TypeScript 60.00%</text>
<text data-testid="lang-name">Python 40.00%</text></svg>'''


class ProfileCardsTest(unittest.TestCase):
    def test_both_layouts_preserve_real_values_and_escape_names(self):
        cards = render(STATS, LANGUAGES)
        self.assertEqual(len(cards), 2)
        for filename, svg in cards.items():
            root = ET.fromstring(svg)
            content = " ".join(root.itertext())
            self.assertIn("Xuan & Loc's GitHub Stats", content)
            self.assertIn("Commits (last year): 167", content)
            self.assertIn("GitHub rank: C", content)
            self.assertIn("Python: 40.00%", content)
            self.assertEqual(root.get("width"), "495" if "mobile" in filename else "1010")

    def test_error_cards_and_invalid_numbers_fail_before_publishing(self):
        with self.assertRaises(ValueError):
            render("<svg/>", LANGUAGES)
        for value in ["unknown", "1,,7", "12,34", "1.2.3k"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                render(STATS.replace(">167<", f">{value}<"), LANGUAGES)

    def test_grouped_and_compact_counts_are_preserved(self):
        for value in ["1,234", "1.2k"]:
            with self.subTest(value=value):
                cards = render(STATS.replace(">167<", f">{value}<"), LANGUAGES)
                self.assertIn(f"Commits (last year): {value}", cards["github-metrics.svg"])

    def test_invalid_chart_data_is_rejected(self):
        for languages in [LANGUAGES.replace("40.00%", "140.00%"), LANGUAGES.replace("40.00%", "30.00%"), LANGUAGES.replace("#3178c6", "url(evil)")]:
            with self.assertRaises(ValueError):
                render(STATS, languages)

    def test_single_language_and_rounded_percentages_work(self):
        single = '<svg><rect data-testid="lang-progress" fill="#123456"/><text data-testid="lang-name">C++ 100.00%</text></svg>'
        self.assertIn("C++: 100.00%", render(STATS, single)["github-metrics.svg"])
        rounded = LANGUAGES.replace("60.00%", "59.99%")
        self.assertIn("59.99%", render(STATS, rounded)["github-metrics.svg"])

import unittest

from scripts.update import (
    _merge_list,
    is_multi_subscription,
    is_single_tvbox_config,
    is_valid_tvbox_config,
    merge_configs,
)


class ConfigValidationTests(unittest.TestCase):
    def test_single_config_requires_sites_array(self):
        self.assertTrue(is_single_tvbox_config({"sites": [{"key": "a"}]}))
        self.assertFalse(is_single_tvbox_config({"sites": "not-an-array"}))
        self.assertFalse(is_single_tvbox_config({"spider": "x"}))

    def test_multi_config_requires_valid_url_entries(self):
        self.assertTrue(is_multi_subscription({"urls": [{"name": "A", "url": "https://example.com/a.json"}]}))
        self.assertFalse(is_multi_subscription({"urls": [{"name": "A"}]}))
        self.assertFalse(is_multi_subscription({"urls": "not-an-array"}))

    def test_validator_accepts_single_or_multi(self):
        self.assertTrue(is_valid_tvbox_config({"sites": [{"key": "a"}]}))
        self.assertTrue(is_valid_tvbox_config({"urls": [{"url": "https://example.com/a.json"}]}))
        self.assertFalse(is_valid_tvbox_config({"sites": "bad", "urls": []}))


class MergeTests(unittest.TestCase):
    def test_same_name_different_urls_are_preserved(self):
        sources = [
            ("a", "A", {"parses": [{"name": "解析", "url": "https://a.example/parse"}]}),
            ("b", "B", {"parses": [{"name": "解析", "url": "https://b.example/parse"}]}),
        ]
        result = _merge_list(sources, "parses")
        self.assertEqual(len(result), 2)

    def test_exact_duplicate_objects_are_removed(self):
        item = {"name": "解析", "url": "https://a.example/parse"}
        sources = [
            ("a", "A", {"parses": [item]}),
            ("b", "B", {"parses": [dict(item)]}),
        ]
        self.assertEqual(_merge_list(sources, "parses"), [item])

    def test_multi_sources_are_excluded_from_single_aggregate(self):
        fetched = [
            ("multi", "多仓", {"urls": [{"name": "A", "url": "https://a.example/a.json"}]}),
        ]
        self.assertIsNone(merge_configs(fetched))

    def test_missing_site_keys_get_stable_unique_keys(self):
        fetched = [
            ("a", "A", {"sites": [{"name": "one"}]}),
            ("b", "B", {"sites": [{"name": "two"}]}),
        ]
        result = merge_configs(fetched)
        self.assertEqual([x["key"] for x in result["sites"]], ["a_site_1", "b_site_1"])

    def test_duplicate_site_keys_are_namespaced(self):
        fetched = [
            ("a", "A", {"sites": [{"key": "vod", "name": "one"}]}),
            ("b", "B", {"sites": [{"key": "vod", "name": "two"}]}),
        ]
        result = merge_configs(fetched)
        self.assertEqual([x["key"] for x in result["sites"]], ["vod", "b_vod"])

    def test_additional_list_fields_are_merged(self):
        fetched = [
            ("a", "A", {
                "sites": [{"key": "a"}],
                "ads": [{"name": "ad-a"}],
                "hosts": [{"host": "a.example"}],
                "ijk": [{"name": "ijk-a"}],
            }),
            ("b", "B", {
                "sites": [{"key": "b"}],
                "ads": [{"name": "ad-b"}],
                "hosts": [{"host": "b.example"}],
                "ijk": [{"name": "ijk-b"}],
            }),
        ]
        result = merge_configs(fetched)
        self.assertEqual(len(result["ads"]), 2)
        self.assertEqual(len(result["hosts"]), 2)
        self.assertEqual(len(result["ijk"]), 2)


if __name__ == "__main__":
    unittest.main()

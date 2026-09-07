import unittest
from src.pipeline import compute_canonical_record_hash
from src.search import PRIORITY_SOCIAL_DOMAINS

class TestCanonicalHashing(unittest.TestCase):
    def setUp(self):
        self.sample_payload = {
            'record_id': 'test-uuid-12345',
            'source_image_sha256': '186aaaa71fdd2ff86bc5bfaca9efc2c77199c67b864bd72cd77d338a0a15e426',
            'matched_url': 'https://instagram.com/p/test-post/',
            'matched_domain': 'instagram.com',
            'match_type': 'social_media_profile',
            'match_confidence': 0.98,
            'result_title': 'Official Verified Creator Post',
            'timestamp_utc': '2026-09-07T12:00:00Z',
        }

    def test_deterministic_serialization(self):
        shuffled = {k: self.sample_payload[k] for k in reversed(list(self.sample_payload.keys()))}
        _, h1 = compute_canonical_record_hash(self.sample_payload)
        _, h2 = compute_canonical_record_hash(shuffled)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_tamper_sensitivity(self):
        _, orig = compute_canonical_record_hash(self.sample_payload)
        t1 = dict(self.sample_payload, result_title='Altered Title')
        _, h_t1 = compute_canonical_record_hash(t1)
        self.assertNotEqual(orig, h_t1)
        t2 = dict(self.sample_payload, match_confidence=0.979)
        _, h_t2 = compute_canonical_record_hash(t2)
        self.assertNotEqual(orig, h_t2)

    def test_solidity_bytes32_compatibility(self):
        _, digest = compute_canonical_record_hash(self.sample_payload)
        raw = bytes.fromhex(digest)
        self.assertEqual(len(raw), 32)

class TestSearchPriority(unittest.TestCase):
    def test_priority_social_domains_coverage(self):
        for p in ['instagram.com', 'x.com', 'linkedin.com', 'facebook.com', 'tiktok.com']:
            self.assertIn(p, PRIORITY_SOCIAL_DOMAINS)

if __name__ == '__main__':
    unittest.main()

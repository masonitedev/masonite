from src.masonite.hashid.middleware import HashIDMiddleware
from src.masonite.hashid.helpers.hashid import hashid
from tests import TestCase


class TestHashID(TestCase):
    def test_hashid_hashes_integer(self):
        assert hashid(10) == "98FqgRu"

    def test_hashid_hashes_several_integers(self):
        assert hashid(10, 20, 30) == "5bQSZgo"

    def test_hashid_decodes_several_integers(self):
        assert hashid("5bQSZgo", decode=True) == (10, 20, 30)

    def test_hashid_roundtrip(self):
        assert hashid(hashid(42), decode=True) == (42,)

    def test_hashid_decodes_non_encoded_value_is_falsey(self):
        assert not hashid("B8I6ub", decode=True)
        # arbitrary alphabet strings must not decode into garbage numbers
        assert not hashid("hello", decode=True)

    def test_hashid_can_decode_dictionary(self):
        assert hashid(
            {
                "id": "98FqgRu",
                "name": "Joe",
            },
            decode=True,
        ) == {"id": 10, "name": "Joe"}

    def test_hashid_can_encode_dictionary(self):
        assert hashid({"id": 10, "name": "Joe"}) == {"id": "98FqgRu", "name": "Joe"}

    def test_middleware(self):
        request = self.make_request(query_string="id=98FqgRu&name=Joe")
        HashIDMiddleware().before(request, None)
        assert request.all() == {"id": 10, "name": "Joe"}

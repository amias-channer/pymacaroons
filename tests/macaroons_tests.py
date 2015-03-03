from __future__ import unicode_literals
import json

from mock import *
from nose.tools import *

from libnacl import crypto_box_NONCEBYTES
from pymacaroons import Macaroon, Verifier
from pymacaroons.serializers import *
from pymacaroons.exceptions import *
from pymacaroons.utils import *
from tests.test_binder import *


class TestMacaroon(object):

    def setup(self):
        pass

    def test_basic_signature(self):
        m = Macaroon(
            location='http://mybank/',
            identifier='we used our secret key',
            key='this is our super secret key; only we should know it'
        )
        assert_equal(
            m.signature,
            'e3d9e02908526c4c0039ae15114115d97fdd68bf2ba379b342aaf0f617d0552f'
        )

    def test_first_party_caveat(self):
        m = Macaroon(
            location='http://mybank/',
            identifier='we used our secret key',
            key='this is our super secret key; only we should know it'
        )
        m.add_first_party_caveat('test = caveat')
        assert_equal(
            m.signature,
            '197bac7a044af33332865b9266e26d493bdd668a660e44d88ce1a998c23dbd67'
        )

    def test_serializing(self):
        m = Macaroon(
            location='http://mybank/',
            identifier='we used our secret key',
            key='this is our super secret key; only we should know it'
        )
        m.add_first_party_caveat('test = caveat')
        assert_equal(
            m.serialize(),
            'MDAxY2xvY2F0aW9uIGh0dHA6Ly9teWJhbmsvCjAwMjZpZGVudGlmaWVyIHdlIHVzZ\
WQgb3VyIHNlY3JldCBrZXkKMDAxNmNpZCB0ZXN0ID0gY2F2ZWF0CjAwMmZzaWduYXR1cmUgGXusegR\
K8zMyhluSZuJtSTvdZopmDkTYjOGpmMI9vWcK'
        )

    def test_serializing_strips_padding(self):
        m = Macaroon(
            location='http://mybank/',
            identifier='we used our secret key',
            key='this is our super secret key; only we should know it'
        )
        m.add_first_party_caveat('test = acaveat')
        assert_equal(
            m.serialize(),
            # In padded base64, this would end with '=='
            ('MDAxY2xvY2F0aW9uIGh0dHA6Ly9teWJhbmsvCjAwMjZpZGVudGlmaWVyIHdlIHVz'
             'ZWQgb3VyIHNlY3JldCBrZXkKMDAxN2NpZCB0ZXN0ID0gYWNhdmVhdAowMDJmc2ln'
             'bmF0dXJlIJRJ_V3WNJQnqlVq5eez7spnltwU_AXs8NIRY739sHooCg')
        )

    def test_serializing_max_length_packet(self):
        m = Macaroon(location='test', identifier='blah', key='secret')
        m.add_first_party_caveat('x' * 65526)  # exactly 0xFFFF
        assert_not_equal(
            m.serialize(),
            None
        )

    def test_serializing_too_long_packet(self):
        m = Macaroon(location='test', identifier='blah', key='secret')
        m.add_first_party_caveat('x' * 65527)  # one byte too long
        assert_raises(
            MacaroonSerializationException,
            m.serialize
        )

    def test_deserializing(self):
        m = Macaroon.deserialize(
            'MDAxY2xvY2F0aW9uIGh0dHA6Ly9teWJhbmsvCjAwMjZpZGVudGlmaW\
VyIHdlIHVzZWQgb3VyIHNlY3JldCBrZXkKMDAxNmNpZCB0ZXN0ID0gY2F2ZWF0CjAwMmZzaWduYXR1\
cmUgGXusegRK8zMyhluSZuJtSTvdZopmDkTYjOGpmMI9vWcK'
        )
        assert_equal(
            m.signature,
            '197bac7a044af33332865b9266e26d493bdd668a660e44d88ce1a998c23dbd67'
        )

    def test_deserializing_accepts_padding(self):
        m = Macaroon.deserialize(
            ('MDAxY2xvY2F0aW9uIGh0dHA6Ly9teWJhbmsvCjAwMjZpZGVudGlmaWVyIHdlIHVz'
             'ZWQgb3VyIHNlY3JldCBrZXkKMDAxN2NpZCB0ZXN0ID0gYWNhdmVhdAowMDJmc2ln'
             'bmF0dXJlIJRJ_V3WNJQnqlVq5eez7spnltwU_AXs8NIRY739sHooCg==')
        )
        assert_equal(
            m.signature,
            '9449fd5dd6349427aa556ae5e7b3eeca6796dc14fc05ecf0d21163bdfdb07a28'
        )

    def test_serializing_json(self):
        m = Macaroon(
            location='http://mybank/',
            identifier='we used our secret key',
            key='this is our super secret key; only we should know it'
        )
        m.add_first_party_caveat('test = caveat')
        assert_equal(
            json.loads(m.serialize(serializer=JsonSerializer()))['signature'],
            "197bac7a044af33332865b9266e26d493bdd668a660e44d88ce1a998c23dbd67"
        )

    def test_deserializing_json(self):
        m = Macaroon.deserialize(
            '{"location": "http://mybank/", "identifier": "we used our secret \
key", "signature": "197bac7a044af33332865b9266e26d493bdd668a660e44d88ce1a998c2\
3dbd67", "caveats": [{"cl": null, "cid": "test = caveat", "vid": null}]}',
            serializer=JsonSerializer()
        )
        assert_equal(
            m.signature,
            '197bac7a044af33332865b9266e26d493bdd668a660e44d88ce1a998c23dbd67'
        )

    def test_serializing_deserializing_json(self):
        m = Macaroon(
            location='http://test/',
            identifier='first',
            key='secret_key_1'
        )
        m.add_first_party_caveat('test = caveat')
        n = Macaroon.deserialize(
            m.serialize(serializer=JsonSerializer()),
            serializer=JsonSerializer()
        )
        assert_equal(m.signature, n.signature)

    def test_verify_first_party_exact_caveats(self):
        m = Macaroon(
            location='http://mybank/',
            identifier='we used our secret key',
            key='this is our super secret key; only we should know it'
        )
        m.add_first_party_caveat('test = caveat')
        v = Verifier()
        v.satisfy_exact('test = caveat')
        verified = v.verify(
            m,
            'this is our super secret key; only we should know it'
        )
        assert_true(verified)

    def test_verify_first_party_general_caveats(self):
        m = Macaroon(
            location='http://mybank/',
            identifier='we used our secret key',
            key='this is our super secret key; only we should know it'
        )
        m.add_first_party_caveat('general caveat')

        def general_caveat_validator(predicate):
            return predicate == 'general caveat'

        v = Verifier()
        v.satisfy_general(general_caveat_validator)
        verified = v.verify(
            m,
            'this is our super secret key; only we should know it'
        )
        assert_true(verified)

    @patch('libnacl.secret.libnacl.utils.rand_nonce')
    def test_third_party_caveat(self, rand_nonce):
        # use a fixed nonce to ensure the same signature
        rand_nonce.return_value = truncate_or_pad(
            b'\0',
            size=crypto_box_NONCEBYTES
        )
        m = Macaroon(
            location='http://mybank/',
            identifier='we used our other secret key',
            key='this is a different super-secret key; \
never use the same secret twice'
        )
        m.add_first_party_caveat('account = 3735928559')
        caveat_key = '4; guaranteed random by a fair toss of the dice'
        predicate = 'user = Alice'
        identifier = 'this was how we remind auth of key/pred'
        m.add_third_party_caveat('http://auth.mybank/', caveat_key, identifier)
        assert_equal(
            m.signature,
            '6b99edb2ec6d7a4382071d7d41a0bf7dfa27d87d2f9fea86e330d7850ffda2b2'
        )

    def test_serializing_macaroon_with_first_and_third_caveats(self):
        m = Macaroon(
            location='http://mybank/',
            identifier='we used our other secret key',
            key='this is a different super-secret key; \
never use the same secret twice'
        )
        m.add_first_party_caveat('account = 3735928559')
        caveat_key = '4; guaranteed random by a fair toss of the dice'
        predicate = 'user = Alice'
        identifier = 'this was how we remind auth of key/pred'
        m.add_third_party_caveat('http://auth.mybank/', caveat_key, identifier)

        n = Macaroon.deserialize(m.serialize())

        assert_equal(
            m.signature,
            n.signature
        )

    @patch('libnacl.secret.libnacl.utils.rand_nonce')
    def test_prepare_for_request(self, rand_nonce):
        # use a fixed nonce to ensure the same signature
        rand_nonce.return_value = truncate_or_pad(
            b'\0',
            size=crypto_box_NONCEBYTES
        )
        m = Macaroon(
            location='http://mybank/',
            identifier='we used our other secret key',
            key='this is a different super-secret key; \
never use the same secret twice'
        )
        m.add_first_party_caveat('account = 3735928559')
        caveat_key = '4; guaranteed random by a fair toss of the dice'
        predicate = 'user = Alice'
        identifier = 'this was how we remind auth of key/pred'
        m.add_third_party_caveat(
            'http://auth.mybank/',
            caveat_key,
            identifier
        )

        discharge = Macaroon(
            location='http://auth.mybank/',
            key=caveat_key,
            identifier=identifier
        )
        discharge.add_first_party_caveat('time < 2015-01-01T00:00')
        protected = m.prepare_for_request(discharge)
        assert_equal(
            protected.signature,
            'b38b26ab29d3724e728427e758cccc16d9d7f3de46d0d811b70b117b05357b9b'
        )

    def test_verify_third_party_caveats(self):
        m = Macaroon(
            location='http://mybank/',
            identifier='we used our other secret key',
            key='this is a different super-secret key; \
never use the same secret twice'
        )
        m.add_first_party_caveat('account = 3735928559')
        caveat_key = '4; guaranteed random by a fair toss of the dice'
        predicate = 'user = Alice'
        identifier = 'this was how we remind auth of key/pred'
        m.add_third_party_caveat('http://auth.mybank/', caveat_key, identifier)

        discharge = Macaroon(
            location='http://auth.mybank/',
            key=caveat_key,
            identifier=identifier
        )
        discharge.add_first_party_caveat('time < 2015-01-01T00:00')
        protected = m.prepare_for_request(discharge)

        v = Verifier()
        v.satisfy_exact('account = 3735928559')
        v.satisfy_exact('time < 2015-01-01T00:00')
        verified = v.verify(
            m,
            'this is a different super-secret key; \
never use the same secret twice',
            discharge_macaroons=[protected]
        )
        assert_true(verified)

    def test_inspect(self):
        m = Macaroon(
            location='http://mybank/',
            identifier='we used our secret key',
            key='this is our super secret key; only we should know it'
        )
        m.add_first_party_caveat('test = caveat')
        assert_equal(m.inspect(), 'location http://mybank/\nidentifier we used\
 our secret key\ncid test = caveat\nsignature 197bac7a044af33332865b9266e26d49\
3bdd668a660e44d88ce1a998c23dbd67')

    def test_verify_third_party_caveat_with_custom_binder(self):
        m = Macaroon(
            location='http://mybank/',
            identifier='we used our other secret key',
            key='this is a different super-secret key; \
never use the same secret twice'
        )
        m.add_first_party_caveat('account = 3735928559')

        # first third party caveat
        caveat_key_1 = '4; guaranteed random by a fair toss of the dice'
        predicate_1 = 'user = Alice'
        identifier_1 = 'this was how we remind auth of key/pred'
        m.add_third_party_caveat('http://auth.mybank/', caveat_key_1, identifier_1)

        # second third party caveat
        caveat_key_2 = '5; guaranteed random by a fair toss of the dice'
        predicate_2 = 'test = caveat'
        identifier_2 = 'reminder for other.service'
        m.add_third_party_caveat('http://other.service/', caveat_key_2, identifier_2)

        discharge_1 = Macaroon(
            location='http://auth.mybank/',
            key=caveat_key_1,
            identifier=identifier_1
        )
        discharge_1.add_first_party_caveat('time < 2015-01-01T00:00')
        protected_1 = m.prepare_for_request(discharge_1, binder_class=HashSignaturesBinder1)

        discharge_2 = Macaroon(
            location='http://other.service/',
            key=caveat_key_2,
            identifier=identifier_2
        )
        discharge_2.add_first_party_caveat('time < 2015-01-01T00:00')
        protected_2 = m.prepare_for_request(discharge_2, binder_class=HashSignaturesBinder2)

        v = Verifier(discharge_binders={identifier_1: HashSignaturesBinder1, 'http://other.service/': HashSignaturesBinder2})
        v.satisfy_exact('account = 3735928559')
        v.satisfy_exact('time < 2015-01-01T00:00')
        verified = v.verify(
            m,
            'this is a different super-secret key; \
never use the same secret twice',
            discharge_macaroons=[protected_1, protected_2]
        )
        assert_true(verified)

from tests.util import setUpModule, tearDownModule
import unittest
from dokomoforms.models import Base

utils = (setUpModule, tearDownModule)


class TestOne(unittest.TestCase):
    def test_one(self):
        self.assertEqual(Base.metadata.schema, 'doko_test')
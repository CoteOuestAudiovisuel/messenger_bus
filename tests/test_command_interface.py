import unittest

from messenger_bus.message_handler import CommandInterface

class UserEmailChanged(CommandInterface):
    email = None
    def __init__(self, payload:dict):
        super().__init__(payload)



class TestCommandInterface(unittest.TestCase):

    def test_contain(self):
        self.assertTrue("email" in UserEmailChanged({"email":"test@test.test"}))

    def test_key_value(self):
        m = UserEmailChanged({"email":"test@test.test"})
        self.assertEqual(m.email,"test@test.test")
        self.assertEqual(m["email"],"test@test.test")

    def test_value(self):
        m = UserEmailChanged({"email": "test@test.test"})
        self.assertEqual(str(m), '{"email": "test@test.test"}')

    def test_equal(self):
        m1 = UserEmailChanged({"email":"test@test.test"})
        m2 = UserEmailChanged({"email":"test@test.test"})
        self.assertEqual(m1,m2)

    def test_unknow_attribute(self):
        with self.assertRaises(AttributeError):
            m2 = UserEmailChanged({"email": "test@test.test","a":"b"})


if __name__ == "__main__":
    unittest.main()
import time
import threading

from virtualbricks import errors
from virtualbricks.tests import unittest, must_test_threads, stubs


class TestFactory(unittest.TestCase):

    def setUp(self):
        self.factory = stubs.FactoryStub()

    def test_creation(self):
        defaults = {
            "id": "0",
            "name": "",
            "filename": ""
        }
        self.assertEquals(self.factory.project_parms, defaults)
        self.assertTrue(hasattr(self.factory, "BRICKTYPES"))

    def test_reset_config(self):
        self.factory.reset_config()
        self.assertEquals(self.factory.bricks, [])
        self.assertEquals(self.factory.events, [])
        self.factory.new_brick("stub", "test_brick")
        self.factory.reset_config()
        self.assertEquals(self.factory.bricks, [])
        self.assertEquals(self.factory.events, [])

    def test_newbrick(self):
        self.assertRaises(errors.InvalidName, self.factory.newbrick, "stub",
                          "")
        self.assertRaises(errors.InvalidName, self.factory.newbrick, "stub",
                          " brick")
        self.factory.newbrick("stub", "test_brick")
        self.assertRaises(errors.InvalidName, self.factory.newbrick, "stub",
                          "test_brick")

    def test_newevent(self):
        self.assertRaises(errors.InvalidName, self.factory.newevent, "event",
                          "")
        self.assertRaises(errors.InvalidName, self.factory.newbrick, "event",
                          " event")
        self.factory.newevent("event", "test_event")
        self.assertRaises(errors.InvalidName, self.factory.newevent, "event",
                          "test_event")
        self.assertTrue(self.factory.newevent("Event", "event1"))
        self.assertFalse(self.factory.newevent("eVeNt", "event2"))


class TestThreadingLocking(unittest.TestCase):

    def setUp(self):
        self.factory = stubs.FactoryStub()

    def test_configfile_synchronized(self):
        st1 = [False]
        st2 = []

        def save1(_):
            st1[0] = True
            time.sleep(0.2)
            st1[0] = False

        cfs = stubs.ConfigFileStub(save1)
        self.factory.configfile = cfs
        self.factory.restore_configfile_real = True

        def save2():
            time.sleep(0.1)
            self.factory.restore_configfile()
            st2.append(st1[0])

        t = threading.Thread(target=save2)
        t.start()
        self.factory.save_configfile()
        t.join()
        self.assertFalse(st2[0])

TestThreadingLocking = unittest.skipUnless(
    must_test_threads(), "threads tests non enabled")(TestThreadingLocking)
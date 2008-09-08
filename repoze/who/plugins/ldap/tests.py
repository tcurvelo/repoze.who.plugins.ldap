# -*- coding: utf-8 -*-
#
# repoze.who.plugins.ldap, LDAP authentication for WSGI applications.
# Copyright (C) 2008 by Gustavo Narea <http://gustavonarea.net/>
#
# This file is part of repoze.who.plugins.ldap
# <http://code.gustavonarea.net/repoze.who.plugins.ldap/>
#
# repoze.who.plugins.ldap is freedomware: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or any later
# version.
#
# repoze.who.plugins.ldap is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# repoze.who.plugins.ldap. If not, see <http://www.gnu.org/licenses/>.

"""Test suite for repoze.who.plugins.ldap"""

import unittest

from dataflake.ldapconnection.tests import fakeldap
from ldap import modlist
from zope.interface.verify import verifyClass
from repoze.who.interfaces import IAuthenticator

from repoze.who.plugins.ldap import LDAPAuthenticatorPlugin


class Base(unittest.TestCase):
    """Base test case for the plugins"""
    
    def _makeEnviron(self, kw=None):
        """Create a fake WSGI environment
        
        This is based on the same method of the test suite of repoze.who.
        
        """
        environ = {}
        environ['wsgi.version'] = (1,0)
        if kw is not None:
            environ.update(kw)
        return environ


#{ Test cases for the plugins


class TestMakeLDAPAuthenticatorPlugin(unittest.TestCase):
    """Tests for the constructor of the L{LDAPAuthenticatorPlugin} plugin"""
    
    def test_without_connection(self):
        self.assertRaises(ValueError, LDAPAuthenticatorPlugin, None,
                          'dc=example,dc=org')
    def test_without_base_dn(self):
        conn = fakeldap.initialize('ldap://example.org')
        self.assertRaises(TypeError, LDAPAuthenticatorPlugin, conn)
        self.assertRaises(ValueError, LDAPAuthenticatorPlugin, conn, None)
    
    def test_with_connection(self):
        conn = fakeldap.initialize('ldap://example.org')
        LDAPAuthenticatorPlugin(conn, 'dc=example,dc=org')
    
    def test_connection_is_str(self):
        LDAPAuthenticatorPlugin('ldap://example.org', 'dc=example,dc=org')
    
    def test_connection_is_unicode(self):
        LDAPAuthenticatorPlugin(u'ldap://example.org', 'dc=example,dc=org')


class TestLDAPAuthenticatorPlugin(Base):
    """Tests for the L{LDAPAuthenticatorPlugin} IAuthenticator plugin"""
    
    base_dn = 'ou=people,dc=example,dc=org'
    
    fakeuser = {
        'dn': 'uid=carla,%s' % base_dn,
        'uid': 'carla',
        'cn': 'Carla Paola',
        'password': 'hello',
        'hashedPassword': '{SHA}qvTGHdzF6KLavt4PO0gs2a6pQ00='}
    
    def setUp(self):
        # Connecting to a fake server with a fake account:
        conn = fakeldap.initialize('ldap://example.org')
        conn.simple_bind_s('Manager', 'some password')
        # Adding a fake user, which is used in the tests
        person_attr = {'cn': [self.fakeuser['cn']],
                       'uid': self.fakeuser['uid'],
                       'userPassword': [self.fakeuser['hashedPassword']]}
        conn.add_s(self.fakeuser['dn'], modlist.addModlist(person_attr))
        self.connection = conn
        # Creating a fake environment:
        self.env  = self._makeEnviron()
        # Loading the plugin:
        self.plugin = LDAPAuthenticatorPlugin(self.connection, self.base_dn)
    
    def tearDown(self):
        self.connection.delete_s(self.fakeuser['dn'])

    def test_implements(self):
        verifyClass(IAuthenticator, LDAPAuthenticatorPlugin, tentative=True)

    def test_authenticate_nologin(self):
        result = self.plugin.authenticate(self.env, None)
        self.assertEqual(result, None)

    def test_authenticate_incomplete_credentials(self):
        identity1 = {'login': self.fakeuser['uid']}
        identity2 = {'password': self.fakeuser['password']}
        result1 = self.plugin.authenticate(self.env, identity1)
        result2 = self.plugin.authenticate(self.env, identity2)
        self.assertEqual(result1, None)
        self.assertEqual(result2, None)

    def test_authenticate_noresults(self):
        identity = {'login': 'i_dont_exist',
                    'password': 'super secure password'}
        result = self.plugin.authenticate(self.env, identity)
        self.assertEqual(result, None)

    def test_authenticate_comparefail(self):
        identity = {'login': self.fakeuser['uid'],
                    'password': 'wrong password'}
        result = self.plugin.authenticate(self.env, identity)
        self.assertEqual(result, None)

    def test_authenticate_comparesuccess(self):
        identity = {'login': self.fakeuser['uid'],
                    'password': self.fakeuser['password']}
        result = self.plugin.authenticate(self.env, identity)
        self.assertEqual(result, self.fakeuser['dn'])
    
    def test_custom_authenticator(self):
        """L{LDAPAuthenticatorPlugin._get_dn} should be overriden with no
        problems"""
        plugin = CustomLDAPAuthenticatorPlugin(self.connection, self.base_dn)
        identity = {'login': self.fakeuser['uid'],
                    'password': self.fakeuser['password']}
        result = plugin.authenticate(self.env, identity)
        expected = 'uid=%s,ou=admins,%s' % (self.fakeuser['uid'], self.base_dn)
        self.assertEqual(result, expected)


# Test cases for plugin utilities


#{ Fixtures


class CustomLDAPAuthenticatorPlugin(LDAPAuthenticatorPlugin):
    """Fake class to test that L{LDAPAuthenticatorPlugin._get_dn} can be
    overriden with no problems"""
    def _get_dn(self, environ, identity):
        try:
            return u'uid=%s,ou=admins,%s' % (identity['login'], self.base_dn)
        except (KeyError, TypeError):
            raise ValueError, ('Could not find the DN from the identity and '
                               'environment')


#}


def suite():
    """
    Return the test suite.
    
    @return: The test suite for the plugin.
    @rtype: C{unittest.TestSuite}
    
    """
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestMakeLDAPAuthenticatorPlugin, "test"))
    suite.addTest(unittest.makeSuite(TestLDAPAuthenticatorPlugin, "test"))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')

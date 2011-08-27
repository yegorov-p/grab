# Copyright: 2011, Grigoriy Petukhov
# Author: Grigoriy Petukhov (http://lorien.name)
# License: BSD
from __future__ import absolute_import
from lxml.html import fromstring
from lxml.cssselect import CSSSelector
from urlparse import urljoin
import re

from grab import DataNotFound


REX_NUMBER = re.compile(r'\d+')
REX_SPACE = re.compile(r'\s', re.U)

class Extension(object):
    export_attributes = ['tree', 'follow_link',
                         'get_node_text', 'find_node_number',
                         'xpath', 'xpath_text', 'xpath_number', 'xpath_list',
                         'css', 'css_text', 'css_number', 'css_list']

    def extra_reset(self, grab):
        grab._lxml_tree = None

    @property
    def tree(self):
        """
        Return lxml ElementTree tree of the document.
        """

        if self._lxml_tree is None:
            body = self.response.unicode_body()
            if self.config['lowercased_tree']:
                body = body.lower()
            self._lxml_tree = fromstring(body)
        return self._lxml_tree

    def follow_link(self, anchor=None, href=None):
        """
        Find link and follow it.
        """

        if anchor is None and href is None:
            raise Exception('You have to provide anchor or href argument')
        self.tree.make_links_absolute(self.config['url'])
        for item in self.tree.iterlinks():
            if item[0].tag == 'a':
                found = False
                text = item[0].text or u''
                url = item[2]
                # if object is regular expression
                if anchor:
                    if hasattr(anchor, 'finditer'):
                        if anchor.search(text):
                            found = True
                    else:
                        if text.find(anchor) > -1:
                            found = True
                if href:
                    if hasattr(href, 'finditer'):
                        if href.search(url):
                            found = True
                    else:
                        if url.startswith(href) > -1:
                            found = True
                if found:
                    url = urljoin(self.config['url'], item[2])
                    return self.request(url=item[2])
        raise DataNotFound('Cannot find link ANCHOR=%s, HREF=%s' % (anchor, href))

    def get_node_text(self, node):
        return self.normalize_space(' '.join(node.xpath('./descendant-or-self::*[name() != "script" and name() != "style"]/text()[normalize-space()]')))

    def find_node_number(self, node):
        return self.find_number(self.get_node_text(node))

    def xpath(self, path, filter=None):
        """
        Get first element which matches the given xpath or raise DataNotFound.
        """

        try:
            return self.xpath_list(path, filter)[0]
        except IndexError:
            raise DataNotFound('Xpath not found: %s' % path)

    def xpath_list(self, path, filter=None):
        """
        Find all elements which match given xpath.
        """

        items = self.tree.xpath(path)
        if filter:
            return [x for x in items if filter(x)]
        else:
            return items 

    def xpath_text(self, path, filter=None):
        """
        Get normalized text of node which matches the given xpath.
        """

        return self.get_node_text(self.xpath(path, filter=filter))

    def xpath_number(self, path, filter=None, ignore_spaces=False):
        """
        Find number in normalized text of node which matches the given xpath.
        """

        return self.find_number(self.xpath_text(path, filter=filter), ignore_spaces=ignore_spaces)

    def css(self, path):
        """
        Get first element which matches the given css path or raise DataNotFound.
        """

        try:
            return self.css_list(path)[0]
        except IndexError:
            raise DataNotFound('CSS path not found: %s' % path)

    def css_list(self, path):
        """
        Find all elements which match given css path.
        """

        return self.tree.cssselect(path)

    def css_text(self, path):
        """
        Get normalized text of node which matches the css path.
        """

        return self.get_node_text(self.css(path))

    def css_number(self, path, ignore_spaces=False):
        """
        Find number in normalized text of node which matches the given css path.
        """

        return self.find_number(self.css_text(path), ignore_spaces=ignore_spaces)

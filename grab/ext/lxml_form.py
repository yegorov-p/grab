# Copyright: 2011, Grigoriy Petukhov
# Author: Grigoriy Petukhov (http://lorien.name)
# License: BSD
from __future__ import absolute_import
from lxml.html import fromstring
from urlparse import urljoin

from ..base import DataNotFound, GrabMisuseError

class Extension(object):
    def extra_reset(self):
        self._lxml_form = None
        self._file_fields = {}

    def choose_form(self, number=None, id=None, name=None):
        """
        Set the default form.
        
        :param number: number of form (starting from zero)
        :param id: value of "id" atrribute
        :param name: value of "name" attribute
        :raises: :class:`DataNotFound` if form not found
        :raises: :class:`GrabMisuseError` if method is called without parameters

        Selected form will be available via `form` atribute of `Grab`
        instance. All form methods will work with defalt form.

        Examples::

            # Select second form
            g.select_form(1)

            # Select by id
            g.select_form(id="register")

            # Select by name
            g.select_form(name="signup")
        """

        if id is not None:
            try:
                self._lxml_form = self.css('form[id="%s"]' % id)
            except IndexError:
                raise DataNotFound("There is no form with id: %s" % id)
        elif name is not None:
            try:
                self._lxml_form = self.css('form[name="%s"]' % name)
            except IndexError:
                raise DataNotFound("There is no form with name: %s" % name)
        elif number is not None:
            try:
                self._lxml_form = self.tree.forms[number]
            except IndexError:
                raise DataNotFound("There is no form with number: %s" % number)
        else:
            raise GrabMisuseError('choose_form methods requires one of (number, id, name) arguments')
                
    @property
    def form(self):
        """
        This attribute points to default form.

        If form was not selected manually then select the form
        which has the biggest number of input elements.

        The form value is just an `lxml.html` form element.

        Example::

            g.go('some URL')
            # Choose form automatically
            print g.form

            # And now choose form manually
            g.choose_form(1)
            print g.form
        """

        if self._lxml_form is None:
            forms = [(idx, len(x.fields)) for idx, x in enumerate(self.tree.forms)]
            idx = sorted(forms, key=lambda x: x[1], reverse=True)[0][0]
            self.choose_form(idx)
        return self._lxml_form

    def set_input(self, name, value):
        """
        Set the value of form element by its `name` attribute.

        :param name: name of element
        :param value: value which should be set to element

        To check/uncheck the checkbox pass boolean value.

        Example::

            g.set_input('sex', 'male')

            # Check the checkbox
            g.set_input('accept', True)
        """

        elem = self.form.inputs[name]

        processed = False
        if getattr(elem, 'type', None) == 'checkbox':
            if isinstance(value, bool):
                elem.checked = value
                processed = True
        
        if not processed:
            # We need to remember origina values of file fields
            # Because lxml will convert UploadContent/UploadFile object to string
            if getattr(elem, 'type', '').lower() == 'file':
                self._file_fields[name] = value
            elem.value = value

    def set_input_by_id(self, _id, value):
        """
        Set the value of form element by its `id` attribute.

        :param _id: id of element
        :param value: value which should be set to element
        """

        name = self.tree.xpath('//*[@id="%s"]' % _id)[0].get('name')
        return self.set_input(name, value)

    def set_input_by_number(self, number, value):
        """
        Set the value of form element by its number in the form

        :param number: number of element
        :param value: value which should be set to element
        """

        elem = self.form.xpath('.//input[@type="text"]')[number]
        return self.set_input(elem.get('name'), value)


    # TODO:
    # Remove set_input_by_id
    # Remove set_input_by_number
    # New method: set_input_by(id=None, number=None, xpath=None)

    def submit(self, submit_name=None, submit_control=None, make_request=True, url=None, extra_post=None):
        """
        Submit form. Take care about all fields which was not set explicitly.
        """

        # TODO: process self.form.inputs
        # Do not used self.form.fields
        # because it does not contains empty fields
        # and also contains data for unchecked checkboxes and etc


        post = self.form_fields()
        submit_controls = []
        for elem in self.form.inputs:
            if elem.tag == 'input' and elem.type == 'submit':
                submit_controls.append(elem)

        # Submit only one element of submit type
        if submit_control is None:
            if submit_controls:
                submit_control = submit_controls[0]

        if submit_control is not None:
            submit_name = submit_control.name

        if submit_name is not None:
            for elem in submit_controls:
                if elem.name != submit_name:
                    if elem.name in post:
                        del post[elem.name]

        if url:
            action_url = urljoin(self.response.url, url)
        else:
            action_url = urljoin(self.response.url, self.form.action)

        if extra_post:
            post.update(extra_post)

        if self.form.method == 'POST':
            if 'multipart' in self.form.get('enctype', ''):
                for key, obj in self._file_fields.items():
                    post[key] = obj
                self.setup(multipart_post=post.items())
            else:
                self.setup(post=post)
            self.setup(url=action_url)

        else:
            url = action_url.split('?')[0] + '?' + self.urlencode(post.items())
            self.setup(url=url)
        if make_request:
            return self.request()
        else:
            return None

    def form_fields(self):
        fields = dict(self.form.fields)
        for elem in self.form.inputs:
            # Ignore elements without name
            if elem.get('name'):
                if elem.tag == 'select':
                    if not fields[elem.name]:
                        if len(elem.value_options):
                            fields[elem.name] = elem.value_options[-1]
                if getattr(elem, 'type', None) == 'radio':
                    if not fields[elem.name]:
                        fields[elem.name] = elem.get('value')
                if getattr(elem, 'type', None) == 'checkbox':
                    if not elem.checked:
                        if elem.name is not None:
                            del fields[elem.name]
        return fields

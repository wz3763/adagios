from django import forms
import okconfig
from configurator import helpers
import re
from django.core.exceptions import ValidationError
import socket
from pynag import Model

class ScanNetworkForm(forms.Form):
    network_address = forms.CharField()
    def clean_network_address(self):
        addr = self.cleaned_data['network_address']
        if addr.find('/') > -1:
            addr,mask = addr.split('/',1)
            if not mask.isdigit(): raise ValidationError("not a valid netmask")
            if not self.isValidIPAddress(addr): raise ValidationError("not a valid ip address")
        else:
            if not self.isValidIPAddress(addr):raise ValidationError("not a valid ip address")
        return self.cleaned_data['network_address']
    def isValidHostname(self,hostname):
        print hostname
        if len(hostname) > 255:
            return False
        if hostname[-1:] == ".":
            hostname = hostname[:-1] # strip exactly one dot from the right, if present
        allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
        for x in hostname.split("."):
            if allowed.match(x) is False: return False
        return True
    def isValidIPAddress(self, ipaddress):
        try: socket.inet_aton(ipaddress)
        except: return False
        return True

class AddGroupForm(forms.Form):
    group_name = forms.CharField()
    alias = forms.CharField()
    force = forms.BooleanField(required=False)

class AddHostForm(forms.Form):
    host_name = forms.CharField()
    address = forms.CharField()
    #description = forms.CharField()
    group_name = forms.ChoiceField()
    force = forms.BooleanField(required=False)
    def clean(self):
        if self.cleaned_data.has_key('host_name'):
            host_name = self.cleaned_data['host_name']
            force = self.cleaned_data['force']
            if not force and host_name in helpers.get_host_names():
                raise forms.ValidationError("Host name %s already exists, use force to overwrite" % host_name)
        return forms.Form.clean(self)
    def __init__(self, *args, **kwargs):
        super(AddHostForm, self).__init__(*args,**kwargs)
        
        # Set choices and initial values for the groups field
        groups = map( lambda x: (x,x), okconfig.get_groups() )
        if self.fields['group_name'].initial is None:
            self.fields['group_name'].initial = "default"
        self.fields['group_name'].choices = groups

class AddTemplateForm(forms.Form):
    # Attributes
    host_name = forms.ChoiceField()
    template_name = forms.ChoiceField()
    force = forms.BooleanField(required=False)
    def __init__(self,*args,**kwargs):
        super(AddTemplateForm, self).__init__(*args, **kwargs)
        
        # Create choices for our hosts and templates
        hosts = helpers.get_host_names()
        hosts = map(lambda x: (x, x), hosts)
        
        templates = okconfig.get_templates()
        templates = map( lambda x: (x, x), templates )        
        
        self.fields['host_name'].choices = hosts
        self.fields['template_name'].choices = templates
        
    def clean(self):
        result = super(AddTemplateForm, self).clean()
        cleaned_data = self.cleaned_data
        host_name = cleaned_data['host_name']
        template_name = cleaned_data['template_name']
        force = cleaned_data['force']
        if not force: 
            if host_name not in okconfig.get_hosts():
                err = "Host does not exist. Use force to overwrite" % (host_name)
                self._errors['host_name'] = self.error_class(err)
            if template_name not in okconfig.get_templates().keys():
                err = "Template %s not found. Use force to overwrite" % (template_name)
                self._errors['template_name'] = self.error_class(err)
        return result

class EditTemplateForm(forms.Form):
    register = forms.BooleanField()
    service_description = forms.CharField()
    def __init__(self, service=Model.Service(), *args, **kwargs):
        self.service = service
        super(forms.Form,self).__init__(*args, **kwargs)
        
        # Run through all the all attributes. Add
        # to form everything that starts with "_"
        self.description = service['service_description']
        self.command_line = service.get_effective_command_line()
        for k in service.keys():
            if k.startswith('_'):
                fieldname="%s::%s::%s" % ( service['host_name'], service['service_description'], k)
                self.fields[fieldname] = forms.CharField(initial=service[k], label=k)

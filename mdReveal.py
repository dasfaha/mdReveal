#coding: utf-8

try:
    import workflow
    import editor
    import keychain
    import dropbox
    import pickle
    import binascii
    ipad = True

except ImportError:
    ipad = False

#action_in = workflow.get_input()

import glob
import sys
import os
import webbrowser
import dropbox
import json
import getpass
import sys
import re
import StringIO
import webbrowser
import requests
import urllib
import os
import tempfile

try:
    #create a secret.py file to store dropbox tokens
    import secret
    dropbox_app_key = secret.dropbox_app_key
    dropbox_app_secret = secret.dropbox_app_secret
except ImportError:
    pass

defaults = {
    "config": {
        "deck": {
            "author": "David Asfaha",
            "reveal_path": "reveal.js/",
            "description": "Deck"
        },
        "output": {
            "deck_location": "/Public/out",
            "media_location": "/Public/out/media"
        }
    }
}


slide_template = """
        <section align=left data-markdown>
                {0}
        </section>
"""

deck_template = """
<!doctype html>
<html lang="en">

        <head>
                <meta charset="utf-8">

                <title>{description}</title

                <meta name="description" content={description}>
                <meta name="author" content={author}>

                <meta name="apple-mobile-web-app-capable" content="yes" />
                <meta name="apple-mobile-web-app-status-bar-style"
content="black-translucent" />

                <link rel="stylesheet" href="{reveal_path}css/reveal.min.css">
                <link rel="stylesheet" href="{reveal_path}css/theme/simple.css" id="theme">

                <!-- For syntax highlighting -->
                <link rel="stylesheet" href="{reveal_path}lib/css/zenburn.css">

                <!-- If the query includes 'print-pdf', use the PDF print sheet -->
                <script>
                        document.write( '<link rel="stylesheet"
href="{reveal_path}css/print/' + ( window.location.search.match(
/print-pdf/gi ) ? 'pdf' : 'paper' ) + '.css" type="text/css"
media="print">' );
                </script>

                <!--[if lt IE 9]>
                <script src="{reveal_path}lib/js/html5shiv.js"></script>
                <![endif]-->
        </head>

        <body>

                <div class="reveal">

                        <!-- Any section element inside of this container is displayed as a slide -->
                        <div class="slides">
                        {slides}
                        </div>


                </div>

                <script src="{reveal_path}lib/js/head.min.js"></script>
                <script src="{reveal_path}js/reveal.min.js"></script>

                <script>

                        // Full list of configuration options available here:
                        // https://github.com/hakimel/reveal.js#configuration
                        Reveal.initialize({{
                                controls: true,
                                progress: true,
                                history: true,
                                center: true,

                                theme: Reveal.getQueryHash().theme, // available themes are in /css/theme
                                transition: Reveal.getQueryHash().transition || 'linear', //
default/cube/page/concave/zoom/linear/none

                                // Optional libraries used to extend on reveal.js
                                dependencies: [
                                        {{ src: '{reveal_path}lib/js/classList.js', condition: function()
{{ return !document.body.classList; }} }},
                                        {{ src: '{reveal_path}plugin/markdown/marked.js', condition:
function() {{ return !!document.querySelector( '[data-markdown]' ); }}
}},
                                        {{ src: '{reveal_path}plugin/markdown/markdown.js', condition:
function() {{ return !!document.querySelector( '[data-markdown]' ); }}
}},
                                        {{ src: '{reveal_path}plugin/highlight/highlight.js', async:
true, callback: function() {{ hljs.initHighlightingOnLoad(); }} }},
                                        {{ src: '{reveal_path}plugin/zoom-js/zoom.js', async: true,
condition: function() {{ return !!document.body.classList; }} }},
                                        {{ src: '{reveal_path}plugin/notes/notes.js', async: true,
condition: function() {{ return !!document.body.classList; }} }}
                                        // {{ src: 'plugin/remotes/remotes.js', async: true, condition:
function() {{ return !!document.body.classList; }} }}
                                ]
                        }});

                </script>

        </body>
</html>
"""

ipad = False

if 'darwin' in sys.platform:
        if len(sys.argv) == 1:
                raise Exception('Please specify a MarkDown file to process')
        file_name = sys.argv[1]

        #TODO: relives on on settings filel in home dir. Change to take into account, command line and create sensible defaults
        #ensure there is a clear precedence command line > config > default
        settings = {}

        user = getpass.getuser()
        config_file = '/Users/{0}/.mdReveal'.format(user)

        try:
                with open(config_file) as f:
                        settings = json.loads(f.read())['config']
        except IOError:
                #use defaults
                pass

        try:
                mk_file = open(file_name)
        except IOError:
                raise Exception('Could not open: {0}'.format(file_name))
                lines = mk_file.readlines()
        #get the file name without extension
        #Works with a file name or a path
        file_name_rgx = re.compile("^(.*/)?(.*)\.(.*)$")
        m = file_name_rgx.match(file_name)
        if m:
                output_name = m.group(2) + '.html'

elif ipad:
    #iPad Editorial setting
    settings = defaults['config']
    lines = editor.get_text()
else:
    raise Exception('Unkwon Platform - Run in Editorial for iPad or OS X')

starts_with_hash = re.compile('^\s*#')
slides = ""
buf = ""
for line in lines:
        if starts_with_hash.match(line) and buf:
                slides += slide_template.format(buf)
                buf = line
        elif not starts_with_hash.match(line) and buf:
            buf += line
        elif starts_with_hash.match(line) and not buf:
                buf = line

settings['deck']['slides'] = slides
deck = deck_template.format(**settings['deck'])

def dropbox_oauth_workflow():

        global app_key, app_secret

        drop_rest = dropbox.rest.RESTClient()
        drop_sess = dropbox.session.DropboxSession(app_key, app_secret, access_type='dropbox',  rest_client=drop_rest)
        oauth_req_token = drop_sess.obtain_request_token()
        u = drop_sess.build_authorize_url(oauth_req_token)
        webbrowser.open(u)
        return drop_sess

if ipad:
        creds = keychain.get_password('mdReveal2', 'David Asfaha')

        if not creds:
                drop_sess = dropbox_oauth_workflow()
        else:
                auth_token_recovered = pickle.loads(binascii.a2b_qp(creds))
                drop_sess = dropbox.session.DropboxSession(app_key, app_secret, access_type='dropbox')
                drop_sess.set_token(auth_token_recovered.key, auth_token_recovered.secret)

        dbClient = dropbox.client.DropboxClient(drop_sess)

        file_path = editor.get_path()

        deck_buffer = StringIO.StringIO(deck)

        if file_path is None:
                print 'No document is open.'
        else:
                file_name = os.path.split(file_path)[1]

        file_name, ext = os.path.splitext(file_name)

        file_name = file_name + '.html'
        file_path = os.path.join(settings['output']['deck_location'], file_name)
        response = dbClient.put_file(file_path, deck_buffer, overwrite=True)
        url_template = r'dl.dropboxusercontent.com/u/7581892/out/'
        if response and response.get('path', '') == file_path:
                url = urllib.quote(url_template + file_name)
                print url
                webbrowser.open(r'http://' + url)


else:
        output_path = os.path.join(settings['output'].get('deck_location', ''), output_name)
        print "To:", output_path

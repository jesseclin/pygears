.. raw:: html

  <link href="_static/css/fontello.css" type="text/css" rel="stylesheet"/>
  <script type="text/javascript" src="_static/autocomplete.js"></script>


  <style type="text/css" media="screen">
    .the-icons {
        font-size: 20px;
        line-height: 28px;
    }
    .code-panel {
        background: white;
        box-shadow: 0px 0px 10px #ccc;
        margin-bottom: 10px;
    }
    .code-panel .header {
        padding: 10px;
        padding-top: 0px;
        min-height: 40px;
        border-top: 1px solid #ececec;
        background-color: #fff;
        text-align: left;
        display: block;
    }
    .code-panel .header .header-item {
        margin-top: 10px;
        margin-left: 5px;
        margin-right: 5px;
        vertical-align: middle;
        display: inline-block;
    }

    #result-div {
        float: right;
    }

    .loader {
        border: 0.15em solid #f3f3f3; /* Light grey */
        border-top: 0.15em solid #3498db; /* Blue */
        border-radius: 50%;
        width: 1em;
        height: 1em;
        animation: spin 2s linear infinite;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    #cmdrun {
         font-size: 14px;
         line-height: 24px;
    }

    #cmdrun:disabled,
    #cmdrun[disabled]{
        padding-left: 27px;
        padding-right: 27px;
        padding-top: 6px;
        padding-bottom: 6px;
        font-size: 20px;
        line-height: 24px;
        border: 1px solid #999999;
        background-color: #cccccc;
        color: #666666;
    }

    #editor {
        position: relative;
        overflow: hidden;
        display: block;
        top: 0;
        right: 0;
        bottom: 0;
        left: 0;
        height: 300px;
    }
    #editor .ace_gutter > .ace_layer{
        background-color: white;
        width: 20px;
    }
    #consoleLog {
        position: relative;
        top: 0;
        bottom: 0;
        left: 0;
        height: 100px;
    }
    #editorContainer {
        border-top: 2px solid #ececec;
        padding-top: 5px;
        border-bottom: 2px solid #ececec;
    }

    #logContainer {
        margin-top: 5px;
    }

  * {
      box-sizing: border-box;
  }

  /*the container must be positioned relative:*/
  .autocomplete {
      position: relative;
      display: inline-block;
  }

  input[type=text] {
      border: 1px solid transparent;
      background-color: #f1f1f1;
      padding: 10px;
      font-family: "Courier New", monospace;
      font-size: 14px;
      background-color: #f1f1f1;
      width: 100%;
  }

  #btn-import-gear {
      background-color: DodgerBlue;
      color: #fff;
      cursor: pointer;
      padding: 8px;
      font-size: 16px;
  }

  .autocomplete-items {
      position: absolute;
      margin-top: 2px;
      border: 3px solid #d4d4d4;
      z-index: 99;
      column-count: 6;
      /*position the autocomplete items to be the same width as the container:*/
      left: 0;

  }

  .autocomplete-items div {
      font-size: 14px;
      font-family: "Courier New", monospace;
      white-space: pre;
      padding: 6px;
      cursor: pointer;
      break-inside: avoid-column;
      background-color: #ffffff;
  }

  /*when hovering an item:*/
  .autocomplete-items div:hover {
      background-color: #e9e9e9; 
  }

  /*when navigating through the items using the arrow keys:*/
  .autocomplete-active {
      background-color: DodgerBlue !important; 
      color: #ffffff; 
  }

  #gearsDescriptionPlaceholder {
      overflow: auto;
      max-height: 290px;
      margin-top: 20px;
  }
  </style>

PyGears LIVE! 
=============

.. raw:: html

    <div class="code-panel">
        <div class="header">
            <button id="cmdrun" class="btn-run header-item" onClick="javascript:runScript()"><i class="icon-cog-alt"></i> Run!</button>
            <div id="result-div" class="btn-group header-item">
                <button type="button" id="btn-result-zip" disabled="disabled" title="Download all result files as an archive"><i class="the-icons icon-download"></i></button>
                <button type="button" id="btn-result-browse" disabled="disabled" title="Browse result files"><i class="the-icons icon-folder-open-1"></i></button>
                <button type="button" id="btn-result-wave" disabled="disabled" title="View waveform"><i class="the-icons icon-menu"></i></button>
            </div>
        </div>

        <div id="editorContainer">
            <div id="editor"></div>
        </div>
        <div id="logContainer">
            <div id="consoleLog"></div>
        </div>
    </div>
    <div class="autocomplete" style="width:200px;">
        <input id="gearSelect" type="text" name="myCountry" placeholder="Search gears" spellcheck="false">
    </div>
    <button type="button" id="btn-import-gear" onClick="javascript:importSelectedGear()" title="Import selected gear"><code style="color: #fff; background-color:transparent"><b>import</b></code></button>
    <div id="gearsDescriptionPlaceholder"></div>
    <iframe id="iframe" hidden></iframe>


.. raw:: html

    <script src="_static/ace/ace.js" type="text/javascript" charset="utf-8"></script>

    <script type="text/javascript">

      function download(url) {
          let a = document.createElement('a')
          a.href = url
          a.download = url.split('/').pop()
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
      }

      function open_new_tab(url) {
          let a = document.createElement('a')
          a.href = url
          a.target = "_blank"
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
      }

      function partial(fn /*, rest args */){
          return fn.bind.apply(fn, Array.apply(null, arguments).slice(1));
      }

      function parseURL(url) {
          var parser = document.createElement('a'),
              params = {},
              queries, split, i;

          // Let the browser do the work
          parser.href = url;

          // Convert query string to object
          queries = parser.search.replace(/^\?/, '').split('&');
          for( i = 0; i < queries.length; i++ ) {
              split = queries[i].split('=');
              params[split[0]] = split[1];
          }
          return {
              protocol: parser.protocol,
              host: parser.host,
              hostname: parser.hostname,
              port: parser.port,
              pathname: parser.pathname,
              search: parser.search,
              params: params,
              hash: parser.hash
          };
      }

      function runScript() {
          var xhttp = new XMLHttpRequest();
          xhttp.onreadystatechange = function() {
              if (this.readyState == 4) {
                  if (this.status != 200) {
                      document.getElementById("cmdrun").innerHTML = 'Run!';
                      document.getElementById("cmdrun").disabled = false;
                      consoleLog.session.insert({
                          row: consoleLog.session.getLength(),
                          column: 0
                      }, "Server error!\n")
                      return;
                  }

                  var jsonResponse = JSON.parse(xhttp.responseText);

                  document.getElementById("cmdrun").innerHTML = '<i class="icon-cog-alt"></i> Run!';
                  document.getElementById("btn-result-zip").onclick = download.bind(
                      null, `${serverName}/results/${jsonResponse['result_id']}/results.zip`);
                  document.getElementById("btn-result-browse").onclick = open_new_tab.bind(
                      null, `${serverName}/results/${jsonResponse['result_id']}/`);
                  document.getElementById("btn-result-wave").onclick = open_new_tab.bind(
                      null, `${serverName}/wavedrom/${jsonResponse['result_id']}/sim/pygears`);

                  document.getElementById("btn-result-zip").disabled = false
                  document.getElementById("btn-result-browse").disabled = false
                  document.getElementById("btn-result-wave").disabled = false
                  document.getElementById("cmdrun").disabled = false;

                  /* console.log(xhttp.responseText); */
                  /* console.log(serverName + jsonResponse['log']) */
                  fetch(serverName + jsonResponse['log'])
                        .then(function(response) {
                            return response.text().then(function(text) {
                                consoleLog.setValue(text, -1);
                            });
                        });
              } else if (this.readyState == 1)  {
                  consoleLog.session.insert({
                      row: consoleLog.session.getLength(),
                      column: 0
                  }, `Running script...\n`)
              }
          };

          document.getElementById("btn-result-zip").disabled = true
          document.getElementById("btn-result-browse").disabled = true
          document.getElementById("btn-result-wave").disabled = true
          document.getElementById("cmdrun").disabled = true;

          document.getElementById("cmdrun").innerHTML = '<div class="loader"></div>';

          consoleLog.setValue("Uploading script...\n", -1);

          xhttp.open("POST", `${serverName}/run`, true);
          xhttp.setRequestHeader("Content-Type", "application/json");
          xhttp.send(JSON.stringify({"script": editor.getValue()}));

          // console.log("Script run");
      }

      function importSelectedGear() {
          var gear = document.getElementById("gearSelect").value;
          if (!(gear in gears)) {return;}

          editor.session.insert({
              row: 0,
              column: 0
          }, `from pygears.lib import ${gear}\n`)

      }

      var serverName = "http://127.0.0.1:5000";
      /* var serverName = "https://www.synchord.com"; */

      document.getElementById("btn-result-zip").disabled = true
      document.getElementById("btn-result-browse").disabled = true
      document.getElementById("btn-result-wave").disabled = true
      document.getElementById("cmdrun").disabled = false;

      var editor = ace.edit("editor");
      editor.session.setMode("ace/mode/python");
      editor.setOption("showPrintMargin", false)
      editor.setOption("fontSize", 14)

      var consoleLog = ace.edit("consoleLog");
      /* editor.setTheme("ace/theme/chrome"); */
      consoleLog.session.setMode("ace/mode/text");
      consoleLog.setReadOnly(true);
      consoleLog.setOption('showLineNumbers', false);
      consoleLog.setOption('showGutter', false);
      consoleLog.setOption('highlightActiveLine', false);
      consoleLog.setOption("showPrintMargin", false);
      consoleLog.setOption("fontSize", 14);

      var url = parseURL(window.location.href);
      if ('file' in url.params) {
          fetch(url.params['file'])
              .then(function(response) {
                  if (response.status == 200) {
                    return response.text().then(function(text) {
                        editor.setValue(text, -1);
                    });
                  }
              });
      } else {
          editor.setValue('from pygears.lib import rng, shred, drv\n' +
                          'from pygears.typing import Uint\n' +
                          '\n' +
                          'drv(t=Uint[4], seq=[10]) | rng | shred', -1);
      }


      var gears = {
          'add': {'page': 'gears/operators.html', 'page-div-id': 'module-add', 'view-div-id': 'operators.add'},
          'accum': {'page': 'gears/reduce.html', 'page-div-id': 'module-reduce', 'view-div-id': 'reduce.accum'},
          'cart': {},
          'ccat': {},
          'chop': {},
          'clip': {},
          'const': {},
          'czip': {},
          'deal': {},
          'decouple': {},
          'demux': {},
          'div': {'page': 'gears/operators.html', 'page-div-id': 'module-add', 'view-div-id': 'module-div'},
          'dreg': {},
          'eq': {'page': 'gears/operators.html', 'page-div-id': 'module-add', 'view-div-id': 'module-eq'},
          'filt': {},
          'flatten': {},
          'fmap': {},
          'funclut': {},
          'group': {},
          'ge': {'page': 'gears/operators.html', 'page-div-id': 'module-add', 'view-div-id': 'module-ge'},
          'gt': {'page': 'gears/operators.html', 'page-div-id': 'module-add', 'view-div-id': 'module-gt'},
          'interlace': {},
          'invert': {'page': 'gears/operators.html', 'page-div-id': 'module-add', 'view-div-id': 'module-invert'},
          'le': {'page': 'gears/operators.html', 'page-div-id': 'module-add', 'view-div-id': 'module-le'},
          'lt': {'page': 'gears/operators.html', 'page-div-id': 'module-add', 'view-div-id': 'module-lt'},
          'mod': {'page': 'gears/operators.html', 'page-div-id': 'module-add', 'view-div-id': 'module-mod'},
          'mul': {'page': 'gears/operators.html', 'page-div-id': 'module-add', 'view-div-id': 'module-mul'},
          'mux': {},
          'ne': {'page': 'gears/operators.html', 'page-div-id': 'module-add', 'view-div-id': 'module-ne'},
          'neg': {'page': 'gears/operators.html', 'page-div-id': 'module-add', 'view-div-id': 'module-neg'},
          'qcnt': {},
          'reduce': {},
          'replicate': {},
          'rng': {},
          'rom': {},
          'sdp': {},
          'serialize': {},
          'shred': {},
          'sieve': {},
          'take': {},
          'unary': {},
      }

      autocomplete(document.getElementById("gearSelect"), Object.keys(gears), function(val) {
          if (!val) {return};
          var iframe = document.getElementById("iframe");
          var div_id;

          if ("page" in gears[val]) {
              iframe.src = gears[val]["page"];
          } else {
              iframe.src = `gears/${val}.html`;
          }

          if ('page-div-id' in gears[val]) {
              div_id = gears[val]["page-div-id"];
          } else {
              div_id = `module-${val}`;
          }


          iframe.onload = function() {
              var div = document.getElementById("gearsDescriptionPlaceholder");
              div.innerHTML = iframe.contentWindow.document.getElementById(div_id).innerHTML;
              if ('view-div-id' in gears[val]) {
                  document.getElementById(gears[val]['view-div-id']).scrollIntoView();
              } else {
                  div.scrollTop = 0;
              }
          };
      });

    </script>

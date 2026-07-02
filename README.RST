====================================================
NOX.CSF reader for the game Nox by Westwood Studios.
====================================================
This tool allows you to manipulate ``nox.csf`` file of the game.

It supports the following actions:

- Full unpacking to JSON format.
- Packing from JSON format back to CSF format.
- Modifying CSF file by using patch files. Patch files describe what to add, remove or set.
- Lookup one or many strings from a CSF file.

System requirements
===================
The script should work on systems where Python 3.7 can run. Theoretically, it can run on 3.6 but then the order of the
CSF keys might not be preserved exactly.


Where to download
=================
You have 2 choices.

1. Download the pyz file from the "Releases" page (csftool) and run it with your Python interpreter.
2. Download the repository/source code and run the ``__main__.py`` file with your Python interpreter.

How to use
==========
Important for Russian localisations
-----------------------------------
**Russian localisations of Nox store text differently!**

Always add ``-r`` flag before the action! Otherwise you will get text interpreted as Latin-1, instead of Windows-1251.

CSF decompilation
-----------------
.. code-block:: console

   noxcsf [-r] decompile nox.csf[, ...]

This example will decompile your ``nox.csf`` into a JSON file named ``nox.csf.json``. If more than one file is given,
all of them will be decompiled in the same way.

The shape of JSON is adapted for manual editing - it should be easier to edit it in text editors like Notepad++ or Kate
compared to standard JSON layout.

The output will have 3 fields:

- "type" - It will always have a value of "csf_data". This is needed to differentiate it from patches.
- "language_index" - An integer, indicating the language of the CSF. The value might not represent the actual language
  of strings stored inside.
- "entries" - A mapping of string variations by their key. Each variation contains 2 fields:

  - "sound". A string specifying the name of the WAV sound to play from DIALOG directory (without extension).
    If sound is not set, it will show ``null`` value.
  - "value". The string itself.

CSF compilation
---------------
.. code-block:: console

   noxcsf [-r] compile nox.csf modded_csf.json

This example will compile a new CSF file ``nox.csf`` from the input file ``nox.csf.json``.

The data shape of the input must match exactly the format described in `CSF decompilation`_. String variations will be
stored in the order of appearance in the JSON file.

**If string variation has no sound use** ``null`` **value, not an empty string!**

CSF patching
------------
.. code-block:: console

   noxcsf [-r] patch nox.csf csf_patch1.json[, ...]

This example will patch CSF file ``nox.csf`` using rules described in the file ``csf_patch1.json``. If more than one
patch is specified, then patches will be merged in RAM before being applied to the CSF file.

This feature allows you to mod CSF files without caring about other strings - very useful for modding, issuing
localisation fixes etc.

CSF patch files are JSON files that use the following structure:

.. code-block:: json

   {
     "type": "csf_patch",
     "format_version": 1,
     "description" : "Example of a patchset",
     "add": {
       "entry1:example1": [{"sound": "WLCMPPL1", "value": "hello_world"}]
     },
     "set": {
       "team.c:NoTeam": [
         {"sound":  null, "value":  "No team, I swear"},
         {"sound":  null, "value":  "No team, really"}
       ]
     },
     "del": [
       "group.c:undefinedGroup"
     ]
   }

- **"add"** operation adds a string variation. Depending on the situation it will do one of the following:

  - If key exists, it will receive new variations.
  - If key does not exist, a new key will be created with specified variations.
- **"set"** operation changes the string variation. Depending on the situation it will do one of the following:

  - If key exists, it will discard the old variations it had and use specified ones.
  - If key does not exist, a new key will be created with specified variations.
- **"del"** operation removes the key from CSF. If a key does not exist, it will be skipped.

Patching rules
^^^^^^^^^^^^^^

1. Patches are applied sequentially in order of specification.
2. Scheduled actions are applied in the order: **del**, then **set**, then **add**.
3. When patches work on the same key, they follow these rules:

   - **del** will discard all previously scheduled actions for the key and marks the key for deletion.
   - **set** will discard all previously scheduled actions for the key and will use specified variations.
   - **add** will add variations or create the key if no **set** action was scheduled before.

String lookup
-------------
.. code-block:: console

   noxcsf [-r] lookup nox.csf "player.c:tooheavy"[, ...]

This example will look up a string ``player.c:tooheavy`` inside the ``nox.csf`` file. If more parameters are given,
they will be looked up sequentially in addition to the first string.

Things to bear in mind:

- Keys are case-insensitive.
- Keys always consist of a category and a name, separated by a colon (:). On Windows systems, when using PowerShell you
  must **wrap the string in double-quotes** so it doesn't confuse your string for key-value parameter pair.
- Values are returned in the form very similar to the one described in the `CSF decompilation`_ section. Below, you can
  see the example.

.. code-block:: console

   $ python3 noxcsf lookup examples/nox.csf player.c:tooheavy
   Loading CSF "examples/nox.csf"...
   Loaded CSF "examples/nox.csf" [English, 6304 strings in 5592 entries].
   player.c:tooheavy:
   {"sound": null, "value": "You are too weighed down to move."}
   {"sound": null, "value": "You are carrying too much to move."}


Important notes
===============
1. This tool will not work for Westwood Studios titles other than Nox, because of the hardcoded CSF version check (Nox
   uses version 2, while Command & Conquer games use version 3).

   If you want this tool to support v3 CSF files, feel free to open an issue so we can discuss the support (I am not
   sure if files differ between versions).
2. Some tools allow for strings with the same keys. This tool, however, will load only
   **the last encountered value of the same key**!
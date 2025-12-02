# aptreader

aptreader is a webapp for downloading and browsing APT repository metadata, packages, and files.

You can point it at an apt repository URL (e.g. `http://archive.ubuntu.com/ubuntu`) and it will download the 
Packages files, parse them, and present you with a web interface to browse the available distribution releases,
components, and packages, view their details, and download package files.

That's the goal, anyway. This initial commit just sets up the project structure and tooling.

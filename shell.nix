let
  pkgs = import <nixpkgs> {};

  python = pkgs.python3.withPackages (p: [
    p.termcolor
  ]);

in
  pkgs.stdenv.mkDerivation {
    name = "release-env";
    buildInputs = [
      python
      pkgs.python3Packages.pylint
      pkgs.python3Packages.pytest
    ];
  }

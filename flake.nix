{
  description = "development environment for your project";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    uiautomator2.url = "path:/home/ai-dev/CustomLibraries/uiautomator2-nix";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    uiautomator2,
  }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfreePredicate = pkg:
          builtins.elem (nixpkgs.lib.getName pkg) ["steam-unwrapped"];
      };

      python = pkgs.python313;

      pythonOverridden = python.override {
        packageOverrides = self: super: {
          adbutils = super.buildPythonPackage rec {
            pname = "adbutils";
            version = "2.9.2";
            format = "pyproject";
            src = super.fetchPypi {
              inherit pname version;
              sha256 = "sha256-beaLQULFTfTb6gckApnAUnFiUxoI6Lr8NsP9GsnEKR4=";
            };
            nativeBuildInputs = with super; [setuptools wheel pbr retry2];
            propagatedBuildInputs = with super; [
              requests
              deprecation
              whichcraft
              packaging
              pillow
            ];
            doCheck = false;
          };

          pyairtable = super.buildPythonPackage rec {
            pname = "pyairtable";
            version = "3.1.1";
            format = "setuptools";
            src = super.fetchPypi {
              inherit pname version;
              sha256 = "sha256-sYX+8SEZ8kng5wSrTksVopCA/Ikq1NVRoQU6G7YJ7y4=";
            };
            propagatedBuildInputs = with super; [requests inflection pydantic];
            doCheck = false;
          };

          uiautomator2 = super.buildPythonPackage rec {
            pname = "uiautomator2";
            version = "3.2.0";
            format = "pyproject";

            # 👇 This is the magic: pull raw source from the local flake
            src = uiautomator2.packages.${system}.src;

            nativeBuildInputs = with super; [setuptools wheel];
            propagatedBuildInputs = with super; [
              self.adbutils
              requests
              lxml
              pillow
              retry2
            ];

            postPatch = ''
              echo "Patching version into uiautomator2..."
              sed -i "s/__version__ = .*/__version__ = \"${version}\"/" uiautomator2/version.py
            '';

            doCheck = false;
            pythonImportsCheck = ["uiautomator2"];
          };
        };
      };

      nixpkgspythondepnames = [
        "openai"
        "pytesseract"
        "opencv-python"
        "opencv4"
        "dnspython"
        "gdown"
        "pyyaml"
        "requests"
        "lxml"
        "pillow"
        "progress"
        "xmltodict"
        "six"
        "logzero"
        "packaging"
        "whichcraft"
        "pbr"
        "pyelftools"
        "pycryptodome"
        "pytest"
        "isort"
        "pytest-cov"
        "ipython"
        "coverage"
        "inflection"
        "pydantic"
        "poetry-core"
        "poetry-dynamic-versioning"
        "python-dotenv"
        "scikit-image"
        "pandas"
        "google-auth"
        "google-auth-oauthlib"
        "google-auth-httplib2"
        "google-api-python-client"
        "scikit-learn"
        "deprecated"
        "filelock"
        "deprecation"
        "pip"
        "setuptools"
        "playwright"
        "beautifulsoup4"
        "pytest-playwright"
      ];

      pythonEnv = pythonOverridden.withPackages (
        ps:
          (map (name: ps.${name}) nixpkgspythondepnames)
          ++ [ps.adbutils ps.pyairtable ps.uiautomator2]
      );
    in {
      devShells.default = pkgs.mkShell {
        packages = [
          pythonEnv
          pkgs.android-tools
          pkgs.tesseract
          pkgs.playwright-driver.browsers

          # Playwright deps
          pkgs.glib
          pkgs.glibc
          pkgs.nss
          pkgs.nspr
          pkgs.dbus
          pkgs.atk
          pkgs.at-spi2-core
          pkgs.cups
          pkgs.gtk3
          pkgs.gtk4
          pkgs.gtkmm3
          pkgs.expat
          pkgs.xorg.libxcb
          pkgs.xorg.libX11
          pkgs.xorg.libXcomposite
          pkgs.xorg.libXdamage
          pkgs.xorg.libXext
          pkgs.xorg.libXfixes
          pkgs.xorg.libXrandr
          pkgs.libxkbcommon
          pkgs.mesa
          pkgs.pango
          pkgs.cairo
          pkgs.udev
          pkgs.alsa-lib
          pkgs.steam-run
        ];

        shellHook = ''
          echo "---------------------------------------------------------------------"
          echo "nix dev shell ready."
          echo "Python environment (3.13) is active with all dependencies."
          echo "  python: $(which python) ($($(which python) --version 2>&1))"
          echo "  pip:    $(which pip)"
          echo ""

          export PLAYWRIGHT_BROWSERS_PATH=${pkgs.playwright-driver.browsers}
          export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true

          echo "---------------------------------------------------------------------"
        '';
      };
    });
}

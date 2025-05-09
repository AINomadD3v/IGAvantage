{
  description = "Development environment for your project";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05"; # or whatever you want to pin
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
  }:
    flake-utils.lib.eachDefaultSystem (
      system: let
        pkgs = import nixpkgs {inherit system;};
        pythonPackages = pkgs.python3Packages;
        addPythonPackage = name: pythonPackages.${name};

        pythonDepsList = [
          "openai"
          "pytesseract"
          "opencv-python"
          "dnspython"
          "gdown"
          "pyaml"
          "pyyaml"
          "requests"
          "lxml"
          "pillow"
          "retry"
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
          "opencv4"
          "scikitimage"
          "pandas"
          "google-auth"
          "google-auth-oauthlib"
          "google-auth-httplib2"
          "google-api-python-client"
          "scikit-learn"
          "deprecated"
          "filelock"
          "deprecation"
        ];

        pythonDeps = builtins.map addPythonPackage (builtins.attrNames (builtins.listToAttrs (map (n: {
            name = n;
            value = null;
          })
          pythonDepsList)));

        customPython = pkgs.python3.withPackages (ps: pythonDeps);

        pyairtable = pythonPackages.buildPythonPackage rec {
          pname = "pyairtable";
          version = "2.2.0";
          format = "setuptools";
          src = pythonPackages.fetchPypi {
            inherit pname version;
            sha256 = "sha256-LTHHU4uYcwE4WKpmkW0dzdf6qLYA9YzBhR26nW957Tc=";
          };
          propagatedBuildInputs = with pythonPackages; [requests inflection pydantic];
          doCheck = false;
        };

        apkutils2 = pythonPackages.buildPythonPackage rec {
          pname = "apkutils2";
          version = "1.0.0";
          format = "setuptools";
          src = pythonPackages.fetchPypi {
            inherit pname version;
            sha256 = "sha256-xa6PhtPr7mpZ/AFNiFB3Qdfz+asYO6s0tE0BH+h4Zgs=";
          };
          propagatedBuildInputs = with pythonPackages; [lxml xmltodict pyelftools pycryptodome];
          postPatch = ''
            cat >> apkutils2/cigam.py << EOF
            class Magic:
                def __init__(self): pass
                def load(self): pass
                def match_buffer(self): pass
            EOF
            sed -i 's/from cigam import Magic/from .cigam import Magic/' apkutils2/__init__.py
          '';
          doCheck = false;
        };

        adbutils = pythonPackages.buildPythonPackage rec {
          pname = "adbutils";
          version = "2.5.0";
          format = "pyproject";
          src = pythonPackages.fetchPypi {
            inherit pname version;
            sha256 = "sha256-CQa70LCVLNrSmDIFVjRYFsfbaOAmL6s0tE0BH+h4Zgs=";
          };
          nativeBuildInputs = with pythonPackages; [poetry-core setuptools pbr];
          propagatedBuildInputs = with pythonPackages; [requests deprecation whichcraft packaging retry pillow apkutils2];
          doCheck = false;
        };

        imutils = pythonPackages.buildPythonPackage rec {
          pname = "imutils";
          version = "0.5.4";
          src = pkgs.fetchurl {
            url = "https://files.pythonhosted.org/packages/source/i/imutils/imutils-${version}.tar.gz";
            sha256 = "094gbnqhyjha5w7wp6f1mq65mwqwb5i4m1600l1m8p4bragpm0h3";
          };
          propagatedBuildInputs = with pythonPackages; [opencv4 numpy scipy matplotlib];
          doCheck = false;
        };

        findit = pythonPackages.buildPythonPackage rec {
          pname = "findit";
          version = "0.5.8";
          format = "setuptools";
          src = pythonPackages.fetchPypi {
            inherit pname version;
            sha256 = "sha256-qbIbEZSqpno+BH9h2ZbjHz9IxFEtsIL5luU1KqWpGcI=";
          };
          propagatedBuildInputs = with pythonPackages; [opencv4 numpy imutils scikitimage];
          postPatch = ''
            sed -i 's/from skimage.measure import compare_ssim/from skimage.metrics import structural_similarity as compare_ssim/' findit/engine/sim.py
          '';
          doCheck = false;
        };

        loguru = pythonPackages.buildPythonPackage rec {
          pname = "loguru";
          version = "0.7.2";
          src = pythonPackages.fetchPypi {
            inherit pname version;
            sha256 = "sha256-5nGlNSJRXzT9QGNA7paMueyvvEs2xnnaA8GP2NC9Uaw=";
          };
          propagatedBuildInputs = [];
          doCheck = false;
        };

        uiautomator2 = pythonPackages.buildPythonPackage rec {
          pname = "uiautomator2";
          version = "3.2.5";
          format = "pyproject";
          src = pythonPackages.fetchPypi {
            inherit pname version;
            sha256 = "sha256-jkFGm6IYFG258Drqs3xLvr9lGwrfTmueXS54DCQ4cuM=";
          };
          nativeBuildInputs = with pythonPackages; [poetry-core poetry-dynamic-versioning];
          propagatedBuildInputs = [adbutils apkutils2 findit];
          doCheck = false;
        };
      in {
        devShells.default = pkgs.mkShell {
          buildInputs =
            [
              customPython
              uiautomator2
              adbutils
              apkutils2
              pyairtable
              findit
              imutils
              loguru
              pkgs.android-tools
            ]
            ++ pythonDeps;

          shellHook = ''
            SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")
            export PYTHONPATH="$SITE_PACKAGES:${uiautomator2}/lib/python3.11/site-packages:${adbutils}/lib/python3.11/site-packages:${apkutils2}/lib/python3.11/site-packages:${pyairtable}/lib/python3.11/site-packages:${findit}/lib/python3.11/site-packages:${imutils}/lib/python3.11/site-packages:${loguru}/lib/python3.11/site-packages:$PYTHONPATH"
            echo "✅ DevShell ready: PYTHONPATH set"
          '';
        };
      }
    );
}

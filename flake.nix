{
  description = "tg-webm-converter";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            python312
            poetry
            ffmpeg
          ];

          shellHook = ''
            echo "tg-webm-converter dev shell"
            echo "Python: $(python3 --version)"
            echo "Poetry: $(poetry --version)"
            echo "FFmpeg: $(ffmpeg -version | head -n1)"
          '';
        };
      }
    );
}

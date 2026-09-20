{
  description = "Entorno de desarrollo ESP32 / ESP32-S3 con ESP-IDF";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";

    esp-dev.url = "github:mirrexagon/nixpkgs-esp-dev";
  };

  outputs = { self, nixpkgs, esp-dev }:
    let
      system = "x86_64-linux";
    in {
      devShells.${system}.default =
        esp-dev.devShells.${system}.esp-idf-full;
    };
}



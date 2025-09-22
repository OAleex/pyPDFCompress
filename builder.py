import os
import sys
import subprocess
import shutil
import platform

def get_program_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_architecture():
    return platform.architecture()[0]

def build_for_platform(platform_name, arch):
    program_name = "pyPDFCompress.py"
    program_path = os.path.join(get_program_dir(), program_name)

    if not os.path.exists(program_path):
        print(f"Error: The file {program_name} was not found!")
        return

    output_dir = os.path.join(get_program_dir(), "dist")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    icon_path = os.path.join(get_program_dir(), "pdf.ico")

    if not os.path.exists(icon_path):
        print("Error: The file pdf.ico was not found!")
        return

    command = []

    if platform_name == "win32":
        command = [
            "pyinstaller", "--onefile", "--windowed", "--icon=" + icon_path,
            "--distpath", output_dir, "--workpath", os.path.join(get_program_dir(), "build"),
            "--specpath", os.path.join(get_program_dir(), "build"), program_path
        ]
    elif platform_name == "darwin":
        command = [
            "pyinstaller", "--onefile", "--windowed", "--icon=" + icon_path,
            "--distpath", output_dir, "--workpath", os.path.join(get_program_dir(), "build"),
            "--specpath", os.path.join(get_program_dir(), "build"), program_path
        ]
    elif platform_name == "linux":
        command = [
            "pyinstaller", "--onefile", "--windowed", "--icon=" + icon_path,
            "--distpath", output_dir, "--workpath", os.path.join(get_program_dir(), "build"),
            "--specpath", os.path.join(get_program_dir(), "build"), program_path
        ]
    else:
        print(f"Platform {platform_name} is not supported!")
        return

    try:
        print(f"Building for {platform_name} {arch}...")
        subprocess.run(command, check=True)
        print(f"Build completed! The executable is located at: {output_dir}")
    except subprocess.CalledProcessError as e:
        print(f"Error building the executable: {e}")
        return

def clean_up():
    build_dir = os.path.join(get_program_dir(), "build")
    dist_dir = os.path.join(get_program_dir(), "dist")

    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)

    print("Temporary files removed.")

def main():
    if sys.platform.startswith("win"):
        platform_name = "win32"
    elif sys.platform == "darwin":
        platform_name = "darwin"
    elif sys.platform.startswith("linux"):
        platform_name = "linux"
    else:
        print(f"Platform {sys.platform} is not supported for the build.")
        return

    arch = get_architecture()
    if arch == "32bit":
        print("32-bit architecture detected.")
    elif arch == "64bit":
        print("64-bit architecture detected.")
    else:
        print(f"Architecture {arch} not recognized.")
        return

    clean_up()

    build_for_platform(platform_name, arch)

if __name__ == "__main__":
    main()

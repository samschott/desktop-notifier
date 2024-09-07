import platform

if platform.system() == "Darwin":
    from .macos import (
        simulate_clicked,
        simulate_dismissed,
        simulate_button_pressed,
        simulate_replied,
    )
else:
    raise NotImplementedError(f"{platform.system()} is not yet supported")

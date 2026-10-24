"""imagen: construye en la VM las imagenes Docker de proyecto.yml > imagenes y crea sus plantillas en GNS3."""
from ..api import http
from ..config import CFG, RAIZ


def imagen(_):
    import paramiko
    ssh_cfg = CFG["ssh"]
    srv = RAIZ / "servicios"
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ssh_cfg["host"], port=ssh_cfg["puerto"], username=ssh_cfg["usuario"], password=ssh_cfg["clave"],
                allow_agent=False, look_for_keys=False)
    sftp = ssh.open_sftp()
    for ruta in sorted(p for p in srv.rglob("*") if p.is_file() and p.name != ".gitkeep"):
        rel = ruta.relative_to(srv).as_posix()
        partes = rel.split("/")[:-1]
        for i in range(len(partes)):
            try:
                sftp.mkdir("/home/gns3/servicios/" + "/".join(partes[:i + 1]))
            except OSError:
                pass
        try:
            sftp.mkdir("/home/gns3/servicios")
        except OSError:
            pass
        sftp.put(str(ruta), f"/home/gns3/servicios/{rel}")
    for im in CFG["imagenes"]:
        _, o, e = ssh.exec_command(f"cd /home/gns3 && docker build -t {im['etiqueta']} {im['ruta']} 2>&1 | tail -15", timeout=900)
        print(o.read().decode())
    existentes = {t["name"] for t in http("GET", "/templates")}
    for im in CFG["imagenes"]:
        if im["plantilla"] not in existentes:
            http("POST", "/templates", {"name": im["plantilla"], "template_type": "docker", "image": im["etiqueta"],
                                        "adapters": 1, "console_type": "telnet", "start_command": "",
                                        "compute_id": "local", "category": "guest", "symbol": ":/symbols/docker_guest.svg"})
            print(f"plantilla {im['plantilla']} creada")


COMANDOS = {"imagen": (imagen, "construye las imagenes Docker en la VM (SSH) y crea sus plantillas", None)}

def valores(valor, rede, master):
    rede = "True"
    master = "True"
    gasto_real = valor
    gasto_rede = 0
    gasto_master = 0
    gasto_virtual = 0
    if rede == "True" and master == "True":
        gasto_virtual = gasto_real * 3
        gasto_rede = gasto_real * 2
        gasto_master = gasto_real * 3

    elif rede == "True" and master == "False":
        gasto_virtual = gasto_real * 2
        gasto_rede = gasto_real * 2
        gasto_master = 0

    elif rede == "False" and master == "True":
        gasto_virtual = gasto_real * 2
        gasto_rede = 0
        gasto_master = gasto_real * 2

        dados = {
            "gasto_real": gasto_real,
            "gasto_rede": gasto_rede,
            "gasto_master": gasto_master,
            "gasto_virtual": gasto_virtual,
        }

        return dados

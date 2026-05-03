from boteco import Boteco
class KdNode:
    def __init__(self, valor, dir, esq, bar, ehFolha, eixo):
        self.valor = valor
        self.dir = dir
        self.esq = esq
        self.bar = bar
        self.ehFolha = ehFolha
        self.eixo = eixo

class KdTree:
    def __init__(self):
        self.raiz = None

    def insertAll(self, Botecos):
        if len(Botecos) > 0:
            self.raiz = self.buildTree(Botecos, 0)

    def buildTree(self, Botecos, eixo):
        if len(Botecos) == 1:
            return KdNode(None, None, None, Botecos[0], True, eixo)
        if eixo % 2 == 0:
            Botecos.sort(key=lambda botecoObj: botecoObj.lon)
        else:
            Botecos.sort(key=lambda botecoObj: botecoObj.lat)
        mediana = len(Botecos) // 2

        if eixo % 2 == 0:
            valor = Botecos[mediana].lon
        else:
            valor = Botecos[mediana].lat
        
        esq = self.buildTree(Botecos[:mediana], eixo + 1)
        dir = self.buildTree(Botecos[mediana:], eixo + 1)
        return KdNode(valor, dir, esq, None, False, eixo)
    
    def search(self, minx, maxx, miny, maxy, lista, eixo, sub):
        if sub is None:
            return
        if sub.ehFolha:
            if minx <= sub.bar.lon <= maxx and miny <= sub.bar.lat <= maxy:
                lista.append(sub.bar) 
            return 
        if eixo % 2 == 0: 
            if sub.valor > maxx:
                self.search(minx, maxx, miny, maxy, lista, eixo + 1, sub.esq)
            elif sub.valor < minx:
                self.search(minx, maxx, miny, maxy, lista, eixo + 1, sub.dir)              
            else:
                self.search(minx, maxx, miny, maxy, lista, eixo + 1, sub.esq)
                self.search(minx, maxx, miny, maxy, lista, eixo + 1, sub.dir)
        else: 
            if sub.valor > maxy:
                self.search(minx, maxx, miny, maxy, lista, eixo + 1, sub.esq)
            elif sub.valor < miny:
                self.search(minx, maxx, miny, maxy, lista, eixo + 1, sub.dir)
            else:
                self.search(minx, maxx, miny, maxy, lista, eixo + 1, sub.esq)
                self.search(minx, maxx, miny, maxy, lista, eixo + 1, sub.dir)
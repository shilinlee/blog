datasets={'banana':{'long':400,'not_long':100,
                    'sweet':350,'not_sweet':150,
                    'yellow':450,'not_yellow':50},
          'orange':{'long':0,'not_long':300,
                    'sweet':150,'not_sweet':150,
                    'yellow':300,'not_yellow':0},
          'other_fruit':{'long':100,'not_long':100,
                    'sweet':150,'not_sweet':50,
                    'yellow':50,'not_yellow':150},
}

def count_total(data):
    '''计算各种水果的总数                                                     
    return {'bananas':500 ...}, 1000
    '''
    count={}
    total=0
    for fruit in data:
        #因为各种水果要么甜要么不甜                                                                                                                                                                         
        #所有可以使用'sweet'和‘not’ sweet 这两种特征的水果数目统计出各种水果的总数                                                                                                                          
        count[fruit] = data[fruit]['sweet']
        count[fruit] += data[fruit]['not_sweet']
        total =+ count[fruit]
    return count, total


def  cal_base_rates(data):
    '''计算各种水果的先验概率(priori probabilities)                                                     
    return {'banana':0.5...}
    '''
    categories, total = count_total(data)
    base_rates={}
    for label in categories:
        priori_prob=categories[label]/total
        base_rates[label]=priori_prob
    return base_rates


def likelihood_prob(data):
    '''计算各个特征值在已知水果下的概率(likelihood probabilities)                                                                                                                                           
    {'banana':{'long:0.8'...}...}'''
    count,_ = count_total(data)
    likelihood={}
    for fruit in data:
        #创建一个新字典，临时存储各个特征的概率                                                                                                                                                             
        attr_prob={}
        for attr in datasets[fruit]:
            #计算各个特征在已知某种水果下的概率                                                                                                                                                             
            attr_prob[attr]=data[fruit][attr]/count[fruit]
        #把某种水果的各个特征的概率放入到likelihood这个字典中                                                                                                                                               
        likelihood[fruit]=attr_prob
    return likelihood


def evidence_prob(data):
    '''虽然各个证据(特征)的概率的概率对分类结果没有影响                                                                                                                                                     
     主要目的是说明一些基本的概念                                                                                                                                                                           
     return {'long':'50%'}'''
    #水果的所有特征                                                                                                                                                                                         
    attrs = list(data['banana'].keys())
    count, total = count_total(data)
    evidence_prob={}
    #计算各种特征的概率                                                                                                                                                                                     
    for attr in attrs:
        attr_total = 0
        for fruit in data:
            attr_total += data[fruit][attr]
        evidence_prob[attr] = attr_total / total
    return evidence_prob


class naive_bayes_classifier:
    
    def __init__(self, data=datasets):
        #初始化贝叶斯分类器
        self._data = datasets
        self._labels=[key for key  in self._data.keys()]
        self._priori_prob=cal_base_rates(self._data)
        self._likelihood_prob=likelihood_prob(self._data)
        self._evidence_prob=evidence_prob(self._data)
        
    def get_label(self, length, sweetness, color):
        #获取某一组特征值的类别
        self._attrs=[length, sweetness, color]
        res={}
        for label in self._labels:
            prob=self._priori_prob[label]
            for attr in self._attrs:
                prob *= self._likelihood_prob[label][attr] / self._evidence_prob[attr]
            res[label]=prob
        return res
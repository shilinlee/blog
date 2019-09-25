import operator
import bayes
import generate_attrs
def main():
    test_datasets = generate_attrs.gen_attrs()
    classfier = bayes.naive_bayes_classifier()
    for data in test_datasets:
        print('特征值:',end='\t') 
        print(data)
        print('预测结果:',end='\t')
        res=classfier.get_label(*data)
        print(res)
        print('水果类别:',end='\t')
        print(sorted(res.items(),key=operator.itemgetter(1),reverse=True)[0][0])
if __name__=='__main__':
    main()
    

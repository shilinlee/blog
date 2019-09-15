ori_data = open('./PRSA_data_2010.1.1-2014.12.31.csv', 'r')
mod_data = open('./data.csv', 'w')

for line in ori_data.readlines():
    cells = line.split(',')
    mod_data.write(cells[1] +'-'+ cells[2] + '-' + cells[3] + ',')
    
    for cell in cells[4:12]:
        mod_data.write(cell+",")
    mod_data.write(cells[12])

ori_data.close()
mod_data.close()
Tracking-Anything路径: 

    /data4/cxx/workplace/Track-Anything/

Wild6D数据集路径: 

    /data4/cxx/dataset/Wild6D_manage/test/

# 1. 启动Tracking-Anything
```shell
cd /data4/cxx/workplace/Track-Anything/
bash run.sh
```

默认在3号卡上生成， 
run.sh内容如下:

```shell
conda activate Track-A
cd /data4/cxx/workplace/Track-Anything/
python app.py --device cuda:3 --port 12211
```

默认运行的显卡为cuda:3
默认端口为12211

# 2. 配置Tunneling映射
<div align=center>
<img src="./assets/p1.png"/>
</div>

# 3. 访问Tracking-Anything服务
确定端口映射和服务启动后，在浏览器访问127.0.0.1:12211即可访问Tracking-Anything服务
<div align=center>
<img src="./assets/p2.png"/>
</div>
<div align=center>
<img src="./assets/p3.png"/>
</div>
<div align=center>
<img src="./assets/p4.png"/>
</div>
处理

    /data4/cxx/dataset/Wild6D_manage/test/

路径下的所有数据集

# 4. 数据集命名解释

数据全部来自于Wild6D的test_set, scene_01000101对应着原本的Wild6D数据集的bottle/0001/1/路径, 其中类别和序号的对应关系如下：

    01:bottle, 02:bowl, 03:camera, 04:can, 05:laptop, 06:mug
    
<br>

    scene_01002120210916181840 

则对应

    /data4/cxx/dataset/Wild6D/test_set

下的
    
    bottle/0021/2021-09-16--18-18-40/images/

<div align=center>
<img src="./assets/p5.png"/>
</div>
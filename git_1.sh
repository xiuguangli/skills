# 适用于本地修改和远程更新不冲突的情况
git stash push -u -m "lxg local changes" && git pull && git stash pop && echo "Done"
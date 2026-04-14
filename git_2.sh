if [ "" = "-m" ] && [ -n "" ]; then
    msg=""
else
    msg="1"
fi
if [ -n "$msg" ]; then
    mkdir -p logs/git_log
    log_file="logs/git_log/$(date +%Y%m%d_%H%M%S).log"
    script -q -c "
        git add .
        echo '==== git status ===='
        git status
        echo
        echo '==== git commit ===='
        git commit -m \"$msg\"
        echo
        echo '==== git push origin main ===='
        git push origin main
    " "$log_file"
    echo \"日志已保存到 $log_file\"
fi
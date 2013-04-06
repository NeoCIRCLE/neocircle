#!/bin/bash

# install xml.vim


mkdir -p ~/.vim/{ftplugin,indent}
cd ~/.vim
wget 'http://www.vim.org/scripts/download_script.php?src_id=16073' -O ftplugin/xml.vim
echo 'let b:did_indent = 1' > indent/xml.vim
for i in docbk xsl html xhtml
do
    ln -s xml.vim ftplugin/$i.vim
    echo 'let b:did_indent = 1' > indent/$i.vim
done


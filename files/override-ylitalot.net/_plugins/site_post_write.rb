Jekyll::Hooks.register :site, :post_write do |jekyll|
  FileUtils.symlink '../../images', '_site/images'
end # module

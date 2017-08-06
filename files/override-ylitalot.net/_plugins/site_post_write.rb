Jekyll::Hooks.register :site, :post_write do |jekyll|
  FileUtils.symlink '../../_images', '_site/images'
end # module

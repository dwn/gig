  def undo_interpolation(res,wtr,x)
    x = 0.00003 if x < 0.00003
    y = (res - wtr*(1.0-x)) / x
    y = 65535 if y > 65535
    y = 0 if y < 0
    return y
  end

  task :remove_watermark => [:environment] do
    mag_max = 65535.0
    pth_wtr = "#{RAILS_ROOT}/public/images/watermark.png"
    Dir.chdir("#{RAILS_ROOT}/public/assets/parts/")
    arr_fdr = Dir.glob('*').select {|f| File.directory? f}.sort!
    ind_file = 0
    arr_fdr.each do |fdr|
      arr_pth_img = Dir["#{Dir.pwd}/#{fdr}/*"]
      next unless arr_pth_img
      arr_pth_img.each do |pth_img|
        ind_file = ind_file + 1
        file_name = File.basename(pth_img)
        pth_res = "#{File.expand_path('~')}/photobank/#{fdr}/#{file_name}"
        next if File.exist?(pth_res) ||
          !(file_name =~ /\.jpg/i ||
          file_name=~ /\.jpeg/i ||
          file_name =~ /\.png/i ||
          file_name =~ /\.bmp/i ||
          file_name =~ /\.gif/i ||
          file_name =~ /\.tiff/i)
        FileUtils.mkdir_p(File.dirname(pth_res))
        img = Magick::ImageList.new(pth_img).first
        wtr = Magick::ImageList.new(pth_wtr).first
        pix_img, pix_wtr, x_img, y_img, x_wtr, y_wtr, w, h = nil,nil,nil,nil,nil,nil,nil,nil
        if (img.columns > wtr.columns)
          x_img = (img.columns - wtr.columns + 1) * 0.5 # The added 1 is for rounding
          x_wtr = 0
          w = wtr.columns
        else
          x_img = 0
          x_wtr = (wtr.columns - img.columns + 1) * 0.5
          w = img.columns
        end
        if (img.rows > wtr.rows)
          y_img = (img.rows - wtr.rows + 1) * 0.5
          y_wtr = 0
          h = wtr.rows
        else
          y_img = 0
          y_wtr = (wtr.rows - img.rows + 1) * 0.5
          h = img.rows
        end
        puts "#{ind_file} -----------------------------------------------"
        puts "PROCESSING #{pth_img}"
        puts "WATERMARK #{pth_wtr}"
        puts "POSITION IN IMAGE #{x_img} #{y_img}"
        puts "POSITION IN WATERMARK #{x_wtr} #{y_wtr}"
        puts "DIMENSION OF WORKING AREA #{w} #{h}"
        puts "DIMENSION OF RESULT #{img.columns} #{img.rows}"
        puts "RESULT #{pth_res}"
        pix_img = img.get_pixels(x_img, y_img, w, h)
        pix_wtr = wtr.get_pixels(x_wtr, y_wtr, w, h)
        res = Magick::Image.new(w, h)
        pix_res = res.get_pixels(0, 0, w, h)
        i = 0
        num_pix = w * h
        num_pix.times do
          p_wtr = pix_wtr[i]
          p_img = pix_img[i]
          p_res = pix_res[i]
          scl = p_wtr.opacity / mag_max
          p_res.red = undo_interpolation(p_img.red, p_wtr.red, scl)
          p_res.green = undo_interpolation(p_img.green, p_wtr.green, scl)
          p_res.blue = undo_interpolation(p_img.blue, p_wtr.blue, scl)
          p_res.opacity = 1
          i += 1
        end
        # Write cropped resultant image into original image
        pix_img_full = img.get_pixels(0, 0, img.columns, img.rows)
        i = 0
        num_pix.times do
          xx = i.to_i % w.to_i
          yy = (i.to_i / w.to_i).to_i
          p_img_full = pix_img_full[(y_img.to_i + yy.to_i).to_i * img.columns.to_i + (x_img.to_i + xx.to_i)]
          p_res = pix_res[(yy.to_i * w.to_i).to_i + xx.to_i]
          p_img_full.red = p_res.red
          p_img_full.green = p_res.green
          p_img_full.blue = p_res.blue
          i += 1
        end
        img.store_pixels(0, 0, img.columns, img.rows, pix_img_full)
        img.write(pth_res)
      end
    end
  end

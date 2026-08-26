global env
fsdbDumpfile "$env(WAVE_DIR)/$env(tc)/$env(TIMESTAMP).fsdb"
fsdbDumpvars 0
fsdbDumpMDA

puts "fsdbDumpfile=$env(WAVE_DIR)/$env(tc)/$env(TIMESTAMP).fsdb"
puts "fsdbDumpvars=0 (full hierarchy)"

run

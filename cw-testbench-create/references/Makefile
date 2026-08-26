#================================================================================
# Environment variable
#================================================================================
# input directory
export RTL_DIR
export MCO_DIR
export TB_DIR
export CDB_DIR
export CVB_DIR

export SNOP_VIP_DIR

# output directore
export LOG_DIR
export WAVE_DIR

# config
export tc
export seed

PROJ_DIR = $(shell realpath ../../../../v0.1)
TB_DIR = $(PROJ_DIR)/verify/gol_top_tb
RTL_DIR = $(PROJ_DIR)/design
MCO_DIR = $(PROJ_DIR)/lib
CDB_DIR = $(PROJ_DIR)/cbb/design
CVB_DIR = $(PROJ_DIR)/cbb/verify
SNOP_VIP_DIR = $(TB_DIR)/component/vip

LOG_DIR = ./output/$(tc).seed$(seed)/log
WAVE_DIR = ./output/$(tc).seed$(seed)/wave


#================================================================================
# Include common makefile
#================================================================================
VCS_VERSION = 2018
VERDI_VERSION = 2018
DEBUG_MODE = 1
include eda_common.mk

#================================================================================
# Main process
#================================================================================

#----------------------------------------
# Option for compile
#----------------------------------------
# snop_vip_opt:
#   SVT_UVM_TECHNOLOGY : Specifies SystemVerilog based VIPs that are compliant with UVM
#   UVM_PACKER_MAX_BYTES: Sets to 1500000 or greater
#   SVT_JTAG_MAX_DATA_WIDTH: Max 'data' signal width.
#   UVM_DISABLE_AUTO_ITEM_RECORDING : Disables the UVM automatic transaction begin and end event triggering and recording
#   SYNOPSYS_SV : Specifies SystemVerilog based VIPs that are compliant with UVM
snop_vip_opt += +define+SVT_UVM_TECHNOLOGY \
						    +define+UVM_PACKER_MAX_BYTES=1500000 \
						    +define+SVT_JTAG_MAX_DATA_WIDTH=41 \
								+define+SVT_JTAG_MAX_INSTRUCTION_WIDTH=41 \
						    +define+UVM_DISABLE_AUTO_ITEM_RECORDING \
						    +define+SYNOPSYS_SV \
						    +incdir+$(SNOP_VIP_DIR)/include/sverilog \
						    +incdir+$(SNOP_VIP_DIR)/src/sverilog/vcs

dut_ft_opt = -f $(RTL_DIR)/gol_top/ft/gol_top.f
dut_ft_opt += -f $(CDB_DIR)/ft/cdb.f
tb_ft_opt = -f $(TB_DIR)/ft/tb.f
comp_user_opt = +define+AXIRAM_INIT_0_F

#----------------------------------------
# Option for run
#----------------------------------------
run_tcl_opt = $(TB_DIR)/script/tcl/run.tcl
tc = tc_sanity_test
timeout = 1
seed = 100
run_user_opt = 

#----------------------------------------
# Option for verdi
#----------------------------------------
top_opt = -top tb_top



test:
	echo "PROJ_DIR=$(PROJ_DIR)"

"""Tests for filename sanitizer utility"""
import pytest
from util.filename_sanitizer import filter_filename, filter_sheet_name


class TestFilterFilename:
    """Tests for filter_filename function"""
    
    def test_empty_filename(self):
        """Test with empty filename"""
        result = filter_filename('')
        assert result == ''
    
    def test_none_filename(self):
        """Test with None filename"""
        result = filter_filename(None)
        assert result == None
    
    def test_no_special_chars(self):
        """Test filename without special characters"""
        result = filter_filename('normal_file.txt')
        assert result == 'normal_file.txt'
    
    def test_colon_replacement(self):
        """Test colon replacement"""
        result = filter_filename('file:name.txt')
        assert result == 'file_name.txt'
    
    def test_backslash_replacement(self):
        """Test backslash replacement"""
        result = filter_filename('file\\name.txt')
        assert result == 'file_name.txt'
    
    def test_forward_slash_replacement(self):
        """Test forward slash replacement"""
        result = filter_filename('file/name.txt')
        assert result == 'file_name.txt'
    
    def test_question_mark_replacement(self):
        """Test question mark replacement"""
        result = filter_filename('file?name.txt')
        assert result == 'file_name.txt'
    
    def test_asterisk_replacement(self):
        """Test asterisk replacement"""
        result = filter_filename('file*name.txt')
        assert result == 'file_name.txt'
    
    def test_left_bracket_replacement(self):
        """Test left bracket replacement"""
        result = filter_filename('file[name.txt')
        assert result == 'file_name.txt'
    
    def test_right_bracket_replacement(self):
        """Test right bracket replacement"""
        result = filter_filename('file]name.txt')
        assert result == 'file_name.txt'
    
    def test_hash_replacement(self):
        """Test hash replacement"""
        result = filter_filename('file#name.txt')
        assert result == 'file_name.txt'
    
    def test_ampersand_replacement(self):
        """Test ampersand replacement"""
        result = filter_filename('file&name.txt')
        assert result == 'file_name.txt'
    
    def test_all_special_chars(self):
        """Test with all special characters"""
        result = filter_filename('file:name\\name/file?name*name[name]name#name&name.txt')
        # 9 special characters replaced with underscores
        assert result == 'file_name_name_file_name_name_name_name_name_name.txt'
    
    def test_custom_replacement_char(self):
        """Test with custom replacement character"""
        result = filter_filename('file:name.txt', replacement='-')
        assert result == 'file-name.txt'
    
    def test_multiple_consecutive_special_chars(self):
        """Test with multiple consecutive special characters"""
        result = filter_filename('file:::name.txt')
        assert result == 'file___name.txt'
    
    def test_special_chars_in_middle(self):
        """Test with special characters in the middle"""
        result = filter_filename('my#special&file.txt')
        assert result == 'my_special_file.txt'
    
    def test_special_chars_at_start(self):
        """Test with special characters at the start"""
        result = filter_filename('#file.txt')
        assert result == '_file.txt'
    
    def test_special_chars_at_end(self):
        """Test with special characters at the end"""
        result = filter_filename('file#.txt')
        assert result == 'file_.txt'
    
    def test_filename_exceeds_255_chars(self):
        """Test filename longer than 255 characters"""
        long_name = 'a' * 260 + '.txt'
        result = filter_filename(long_name)
        assert len(result) <= 255
        assert result.endswith('.txt')
    
    def test_filename_exceeds_255_no_extension(self):
        """Test filename longer than 255 characters without extension"""
        long_name = 'b' * 260
        result = filter_filename(long_name)
        assert len(result) <= 255
    
    def test_very_long_name_with_extension(self):
        """Test very long filename with extension"""
        long_name = 'c' * 250 + '.txt'
        result = filter_filename(long_name)
        assert len(result) <= 255
        assert result.endswith('.txt')
    
    def test_empty_after_cleaning(self):
        """Test filename that becomes empty after cleaning"""
        result = filter_filename('###')
        # After cleaning, '###' becomes '___', which is not empty/whitespace
        # So it should return '___'
        assert result == '___'
    
    def test_whitespace_only_after_cleaning(self):
        """Test filename that becomes whitespace only after cleaning"""
        result = filter_filename('   ')
        assert result == 'unnamed_file'
    
    def test_hidden_file(self):
        """Test hidden file (starts with dot)"""
        result = filter_filename('.hidden')
        assert result == '.hidden'
    
    def test_hidden_file_with_special_chars(self):
        """Test hidden file with special characters"""
        result = filter_filename('.#hidden#')
        assert result == '._hidden_'
    
    def test_file_without_extension(self):
        """Test file without extension"""
        result = filter_filename('filename')
        assert result == 'filename'
    
    def test_file_with_multiple_dots(self):
        """Test file with multiple dots"""
        result = filter_filename('file.name.with.dots.txt')
        assert result == 'file.name.with.dots.txt'
    
    def test_file_with_special_chars_in_extension(self):
        """Test file with special characters in extension"""
        result = filter_filename('file.txt#')
        assert result == 'file.txt_'
    
    def test_complex_filename(self):
        """Test complex filename with multiple special characters"""
        result = filter_filename('Project: Report [2024]/Final&Version#.xlsx')
        assert result == 'Project_ Report _2024__Final_Version_.xlsx'
    
    def test_unicode_characters(self):
        """Test filename with unicode characters"""
        result = filter_filename('文件_文件.txt')
        assert result == '文件_文件.txt'
    
    def test_unicode_with_special_chars(self):
        """Test filename with unicode and special characters"""
        result = filter_filename('文件:测试.txt')
        assert result == '文件_测试.txt'


class TestFilterSheetName:
    """Tests for filter_sheet_name function"""
    
    def test_empty_sheet_name(self):
        """Test with empty sheet name"""
        result = filter_sheet_name('')
        assert result == 'Sheet'
    
    def test_none_sheet_name(self):
        """Test with None sheet name"""
        result = filter_sheet_name(None)
        assert result == 'Sheet'
    
    def test_no_special_chars(self):
        """Test sheet name without special characters"""
        result = filter_sheet_name('正常工作表')
        assert result == '正常工作表'
    
    def test_colon_replacement(self):
        """Test colon replacement"""
        result = filter_sheet_name('工作:表')
        assert result == '工作_表'
    
    def test_backslash_replacement(self):
        """Test backslash replacement"""
        result = filter_sheet_name('工作\\表')
        assert result == '工作_表'
    
    def test_forward_slash_replacement(self):
        """Test forward slash replacement"""
        result = filter_sheet_name('工作/表')
        assert result == '工作_表'
    
    def test_question_mark_replacement(self):
        """Test question mark replacement"""
        result = filter_sheet_name('工作?表')
        assert result == '工作_表'
    
    def test_asterisk_replacement(self):
        """Test asterisk replacement"""
        result = filter_sheet_name('工作*表')
        assert result == '工作_表'
    
    def test_left_bracket_replacement(self):
        """Test left bracket replacement"""
        result = filter_sheet_name('工作[表')
        assert result == '工作_表'
    
    def test_right_bracket_replacement(self):
        """Test right bracket replacement"""
        result = filter_sheet_name('工作]表')
        assert result == '工作_表'
    
    def test_all_excel_illegal_chars(self):
        """Test with all Excel illegal characters"""
        result = filter_sheet_name('工作:名\\名/名?名*名[名]名')
        assert result == '工作_名_名_名_名_名_名_名'
    
    def test_custom_replacement_char(self):
        """Test with custom replacement character"""
        result = filter_sheet_name('工作:表', replacement='-')
        assert result == '工作-表'
    
    def test_sheet_name_exceeds_31_chars(self):
        """Test sheet name longer than 31 characters"""
        long_name = 'a' * 35
        result = filter_sheet_name(long_name)
        assert len(result) == 31
        assert result == 'a' * 31
    
    def test_whitespace_only(self):
        """Test sheet name that is whitespace only"""
        result = filter_sheet_name('   ')
        assert result == 'Sheet'
    
    def test_hash_and_ampersand_allowed(self):
        """Test that # and & are allowed in sheet names"""
        result = filter_sheet_name('工作#表&1')
        assert result == '工作#表&1'
    
    def test_complex_sheet_name(self):
        """Test complex sheet name"""
        result = filter_sheet_name('项目报告 [2024]#最终版&修订')
        assert result == '项目报告 _2024_#最终版&修订'
